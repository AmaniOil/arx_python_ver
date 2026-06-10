from pathlib import Path
import tempfile
import unittest

from safepub.csv_io import (
    read_data_csv,
    read_hierarchy_csv,
    read_hierarchies_from_paths,
    write_data_csv,
)


class TestCSVIO(unittest.TestCase):
    def test_read_data_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.csv"
            path.write_text("age,gender\n34,male\n45,female\n", encoding="utf-8")

            rows = read_data_csv(path)

        self.assertEqual(
            rows,
            (
                {"age": "34", "gender": "male"},
                {"age": "45", "gender": "female"},
            ),
        )

    def test_read_hierarchy_csv_without_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "age.csv"
            path.write_text("34,<50,*\n45,<50,*\n66,>=50,*\n", encoding="utf-8")

            hierarchy = read_hierarchy_csv(path, has_header=False)

        self.assertEqual(hierarchy["34"], ("34", "<50", "*"))
        self.assertEqual(hierarchy["66"], ("66", ">=50", "*"))

    def test_read_hierarchy_csv_with_auto_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "age.csv"
            path.write_text(
                "value,level1,level2\n34,<50,*\n45,<50,*\n",
                encoding="utf-8",
            )

            hierarchy = read_hierarchy_csv(path)

        self.assertEqual(set(hierarchy), {"34", "45"})

    def test_read_hierarchies_from_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            age_path = Path(tmpdir) / "age.csv"
            gender_path = Path(tmpdir) / "gender.csv"
            age_path.write_text("34,<50,*\n45,<50,*\n", encoding="utf-8")
            gender_path.write_text("male,*\nfemale,*\n", encoding="utf-8")

            hierarchies = read_hierarchies_from_paths(
                {"age": age_path, "gender": gender_path},
                has_header=False,
            )

        self.assertEqual(hierarchies["age"]["34"], ("34", "<50", "*"))
        self.assertEqual(hierarchies["gender"]["male"], ("male", "*"))

    def test_write_data_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.csv"
            write_data_csv(
                path,
                [{"age": "<50", "gender": "*"}, {"age": ">=50", "gender": "*"}],
            )

            text = path.read_text(encoding="utf-8")

        self.assertIn("age,gender", text)
        self.assertIn("<50,*", text)


if __name__ == "__main__":
    unittest.main()
