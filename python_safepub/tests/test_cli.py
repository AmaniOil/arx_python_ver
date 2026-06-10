from pathlib import Path
import tempfile
import unittest

from safepub.cli import (
    main,
    parse_hierarchy_arguments,
    prompt_for_search_budget_ratio,
    prompt_for_missing_hierarchy_paths,
    resolve_search_budget,
)


class TestCLI(unittest.TestCase):
    def test_resolve_absolute_search_budget(self):
        data_dependent, budget = resolve_search_budget(
            epsilon=2.0,
            data_dependent=False,
            dp_search_budget=0.1,
            dp_search_budget_ratio=None,
        )
        self.assertTrue(data_dependent)
        self.assertAlmostEqual(budget, 0.1)

    def test_resolve_ratio_search_budget(self):
        data_dependent, budget = resolve_search_budget(
            epsilon=2.0,
            data_dependent=False,
            dp_search_budget=0.0,
            dp_search_budget_ratio=0.05,
        )
        self.assertTrue(data_dependent)
        self.assertAlmostEqual(budget, 0.1)

    def test_data_dependent_defaults_to_ten_percent_search_budget(self):
        data_dependent, budget = resolve_search_budget(
            epsilon=2.0,
            data_dependent=True,
            dp_search_budget=0.0,
            dp_search_budget_ratio=None,
        )
        self.assertTrue(data_dependent)
        self.assertAlmostEqual(budget, 0.2)

    def test_prompt_for_search_budget_ratio_uses_default_on_empty(self):
        answers = iter([""])
        ratio = prompt_for_search_budget_ratio(input_func=lambda prompt: next(answers))
        self.assertAlmostEqual(ratio, 0.10)

    def test_prompt_for_search_budget_ratio_accepts_user_value(self):
        answers = iter(["0.05"])
        ratio = prompt_for_search_budget_ratio(input_func=lambda prompt: next(answers))
        self.assertAlmostEqual(ratio, 0.05)

    def test_parse_hierarchy_arguments(self):
        parsed = parse_hierarchy_arguments(["age=age.csv", "gender=gender.csv"])
        self.assertEqual(parsed, {"age": "age.csv", "gender": "gender.csv"})

    def test_prompt_for_missing_hierarchy_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            age_path = Path(tmpdir) / "age.csv"
            age_path.write_text("34,<50,*\n", encoding="utf-8")
            answers = iter([str(age_path)])

            prompted = prompt_for_missing_hierarchy_paths(
                ("age",),
                input_func=lambda prompt: next(answers),
            )

        self.assertEqual(prompted, {"age": str(age_path)})

    def test_main_reads_csvs_and_writes_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "data.csv"
            age_path = Path(tmpdir) / "age.csv"
            gender_path = Path(tmpdir) / "gender.csv"
            output_path = Path(tmpdir) / "out.csv"

            data_path.write_text(
                "\n".join(
                    [
                        "age,gender",
                        "34,male",
                        "45,female",
                        "66,male",
                        "70,female",
                        "36,male",
                        "52,female",
                        "39,male",
                        "61,female",
                        "44,male",
                        "73,female",
                        "31,male",
                        "58,female",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            age_path.write_text(
                "\n".join(
                    [
                        "34,<50,*",
                        "45,<50,*",
                        "66,>=50,*",
                        "70,>=50,*",
                        "36,<50,*",
                        "52,>=50,*",
                        "39,<50,*",
                        "61,>=50,*",
                        "44,<50,*",
                        "73,>=50,*",
                        "31,<50,*",
                        "58,>=50,*",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            gender_path.write_text("male,*\nfemale,*\n", encoding="utf-8")

            exit_code = main(
                [
                    "--data",
                    str(data_path),
                    "--qi",
                    "age",
                    "gender",
                    "--hierarchy",
                    f"age={age_path}",
                    "--hierarchy",
                    f"gender={gender_path}",
                    "--epsilon",
                    "2.0",
                    "--delta",
                    "0.5",
                    "--deterministic",
                    "--output",
                    str(output_path),
                    "--hierarchy-header",
                    "no",
                ]
            )

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("age,gender", output_text)
        self.assertIn("*,*", output_text)

    def test_main_uses_requested_output_delimiter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "data.csv"
            age_path = Path(tmpdir) / "age.csv"
            output_path = Path(tmpdir) / "out.csv"

            data_path.write_text(
                "\n".join(
                    [
                        "age;label",
                        "34;a",
                        "45;b",
                        "66;c",
                        "70;d",
                        "36;e",
                        "52;f",
                        "39;g",
                        "61;h",
                        "44;i",
                        "73;j",
                        "31;k",
                        "58;l",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            age_path.write_text(
                "\n".join(
                    [
                        "34;<50;*",
                        "45;<50;*",
                        "66;>=50;*",
                        "70;>=50;*",
                        "36;<50;*",
                        "52;>=50;*",
                        "39;<50;*",
                        "61;>=50;*",
                        "44;<50;*",
                        "73;>=50;*",
                        "31;<50;*",
                        "58;>=50;*",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--data",
                    str(data_path),
                    "--qi",
                    "age",
                    "--hierarchy",
                    f"age={age_path}",
                    "--epsilon",
                    "2.0",
                    "--delta",
                    "0.5",
                    "--deterministic",
                    "--delimiter",
                    ";",
                    "--output",
                    str(output_path),
                    "--hierarchy-header",
                    "no",
                ]
            )

            output_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("age;label", output_text)


if __name__ == "__main__":
    unittest.main()
