# SafePub Python版 使い方ガイド (How to Use)

ARX の SafePub((ε, δ)-差分プライバシー匿名化)を Python に移植したものの使い方ガイドです。
実装の技術的な詳細・Java版との対応関係は [README.md](README.md)(英語)を参照してください。

## 1. 前提条件

- Python 3.10 以上(3.13 で動作確認済み)
- 外部ライブラリ不要(標準ライブラリのみで動作)
- このリポジトリを clone 済みであること

```powershell
git clone https://github.com/AmaniOil/arx_python_ver.git
cd arx_python_ver
```

## 2. セットアップ

リポジトリ直下で `PYTHONPATH` を設定します(ターミナルを開くたびに1回)。

Windows (PowerShell):

```powershell
$env:PYTHONPATH = 'python_safepub'
```

Linux / macOS (bash):

```bash
export PYTHONPATH=python_safepub
```

## 3. 動作確認

```powershell
# ユニットテスト(58件すべて OK になれば正常)
python -m unittest discover -s python_safepub/tests

# 内蔵デモ(小さなデータでデータ依存版と固定スキーム版を実行)
python -m safepub.demo
```

## 4. 基本の実行(データ依存 SafePub)

指数メカニズムで一般化レベルを探索する、ARX のデータ依存差分プライバシーに相当するモードです。
リポジトリ同梱の adult データセット(30,162行)での実行例:

```powershell
python -m safepub.cli `
  --data data/adult.csv `
  --qi age sex workclass `
  --hierarchy age=data/adult_hierarchy_age.csv `
  --hierarchy sex=data/adult_hierarchy_sex.csv `
  --hierarchy workclass=data/adult_hierarchy_workclass.csv `
  --epsilon 2.0 `
  --delta 0.00001 `
  --data-dependent `
  --delimiter ';' `
  --hierarchy-header no `
  --output python_safepub/outputs/result.csv
```

行末のバッククォート(`` ` ``)は PowerShell の行継続です。bash の場合は `\` に読み替え、
先頭を `PYTHONPATH=python_safepub python3 -m safepub.cli` としてください。

### 出力サマリーの読み方

```text
search budget: 0.2                             ← 探索に使う ε(既定: ε の 10%)
anonymization budget: 1.8                      ← 匿名化に使う ε
score function: safepub_precision                  ← 探索に使った品質モデル
levels: (2, 0, 0)                              ← 選ばれた一般化レベル(--qi の順)
utility value (ARX ILScore, higher is better): -115.19...
                                               ← 解のスコア(Java版 ARX と同じ出力)
k: 92                                          ← SafePub の k 閾値
beta: 0.834701111778                           ← サンプリング確率
sampled rows: 25174 / 30162                    ← β でサンプルされた行数
suppressed sampled rows (class < k): 1559      ← k 未満の同値類で抑制された行
non-sampled rows (suppressed in output): 4988  ← サンプル外(出力では抑制)
released rows: 23615 / 30162                   ← 実際に内容が公開される行数
```

- スコアは「高いほど良い」値です。Precision / Loss / Discernibility / Entropy では負、
  AECS / Classification では正になります(Java版 ARX と同じ挙動)。
- サンプリングは毎回ランダムなので、結果は実行ごとに変わります。

### 出力 CSV の形式

出力 CSV は**入力と同じ行数**です(ARX の出力ハンドルと同じ形式)。
抑制された行(サンプル外、または同値類サイズが k 未満)は**全列が `*`** になります。
公開対象の行だけが必要な場合は、全列 `*` の行を除外してください。例:

```powershell
Import-Csv python_safepub/outputs/result.csv -Delimiter ';' |
  Where-Object { $_.age -ne '*' -or $_.sex -ne '*' -or $_.workclass -ne '*' } |
  Export-Csv released_only.csv -Delimiter ';' -NoTypeInformation
```

## 5. 品質モデル(スコア関数)の選択

`--utility-metric` で、探索を駆動する ARX の品質モデルを選べます。
Java版でデータ依存 DP に使える6種すべてに対応しています。

| `--utility-metric`   | 品質モデル               | スコア符号 |
|----------------------|--------------------------|-----------|
| `safepub_precision`      | Precision(既定)        | 負        |
| `safepub_loss`           | Loss(粒度)             | 負        |
| `safepub_discernibility` | Discernibility           | 負        |
| `safepub_entropy`        | 非一様エントロピー       | 負        |
| `safepub_aecs`           | 平均同値類サイズ         | 正        |
| `safepub_classification` | 分類精度                 | 正        |

例: Discernibility を有用性に据える場合

```powershell
python -m safepub.cli ... --data-dependent --utility-metric safepub_discernibility
```

`safepub_classification` のみ、目的変数(ターゲット列)の指定が必須です:

```powershell
python -m safepub.cli ... --data-dependent `
  --utility-metric safepub_classification `
  --response-variable salary-class
```

目的変数は準識別子でも非準識別子でも構いません。`--response-variable` は複数回指定できます。

## 6. データ非依存 SafePub(固定スキーム)

一般化レベルを事前に固定し、ε 全額を匿名化に使うモードです
(ARX の `DataGeneralizationScheme` に相当)。**レベルか度合いの指定が必須**です。

```powershell
python -m safepub.cli `
  --data data/adult.csv `
  --qi age sex workclass `
  --hierarchy age=data/adult_hierarchy_age.csv `
  --hierarchy sex=data/adult_hierarchy_sex.csv `
  --hierarchy workclass=data/adult_hierarchy_workclass.csv `
  --epsilon 2.0 `
  --delta 0.00001 `
  --generalization-degree medium `
  --generalization-level age=2 `
  --delimiter ';' `
  --hierarchy-header no `
  --output python_safepub/outputs/fixed_result.csv
```

- `--generalization-level 属性=レベル` … 属性ごとの明示指定(優先)
- `--generalization-degree` … 指定のない属性に適用する度合い。
  `none` / `low` / `low_medium` / `medium` / `medium_high` / `high` / `complete` から選択。
  レベルは ARX と同じ `round(係数 × 最大レベル)` で決まります。

このモードの `utility value` は通常の Precision 情報損失(正の値・小さいほど良い)です。
これも Java版と同じ挙動です(固定スキームでは通常の情報損失を計測するため)。

## 7. 自分の CSV データで使う

必要なもの:

1. **データ CSV** — ヘッダ行つき
2. **準識別子ごとの階層 CSV** — ARX 形式(1列目が原値、右の列ほど一般化)

階層 CSV の例(`age.csv`):

```csv
34,<50,*
45,<50,*
66,>=50,*
70,>=50,*
```

実行例:

```powershell
python -m safepub.cli `
  --data mydata.csv `
  --qi age gender zipcode `
  --epsilon 2.0 `
  --delta 0.00001 `
  --data-dependent `
  --output anonymized.csv
```

`--hierarchy` を省略した属性は実行時に対話的にファイルパスを聞かれます。

## 8. 主なオプション一覧

| オプション | 説明 |
|---|---|
| `--data PATH` | 入力データ CSV(省略時は対話入力) |
| `--qi 列名...` | 準識別子の列名(スペースまたはカンマ区切り) |
| `--hierarchy 属性=PATH` | 属性ごとの階層 CSV |
| `--epsilon` / `--delta` | 差分プライバシーのパラメータ(必須)。δ は 1/行数 より小さい値を推奨 |
| `--data-dependent` | データ依存探索を有効化(探索バジェット既定: ε の 10%) |
| `--dp-search-budget X` | 探索バジェットを絶対値で指定(0 < X < ε) |
| `--dp-search-budget-ratio X` | 探索バジェットを ε に対する割合で指定 |
| `--prompt-search-budget` | 探索バジェット割合を対話的に入力(空 Enter で 0.10) |
| `--search-expansion-limit N` | 探索ステップ数上限(既定: ローカル格子サイズ − 1) |
| `--utility-metric` | 探索に使う品質モデル(上記6種、既定 `safepub_precision`) |
| `--response-variable 列名` | `safepub_classification` の目的変数(複数可) |
| `--generalization-level 属性=N` | 固定スキームのレベル(データ非依存) |
| `--generalization-degree` | 固定スキームの度合い(データ非依存) |
| `--delimiter ';'` | CSV 区切り文字(省略時は自動判定) |
| `--hierarchy-header yes/no/auto` | 階層 CSV のヘッダ有無(既定: 自動判定) |
| `--output PATH` | 匿名化 CSV の出力先 |
| `--deterministic` | 乱数を固定シード化。**検証用のみ**(プライバシー保証が無効になるため本番では使わないこと) |

## 9. Python コードから使う

```python
from safepub import safe_pub_anonymize
from safepub.csv_io import read_data_csv, read_hierarchies_from_paths

data = read_data_csv("data/adult.csv", delimiter=";")
hierarchies = read_hierarchies_from_paths(
    {
        "age": "data/adult_hierarchy_age.csv",
        "sex": "data/adult_hierarchy_sex.csv",
        "workclass": "data/adult_hierarchy_workclass.csv",
    },
    delimiter=";",
    has_header=False,
)

result = safe_pub_anonymize(
    data,
    ("age", "sex", "workclass"),
    hierarchies,
    epsilon=2.0,
    delta=1e-5,
    data_dependent=True,
    utility_metric="safepub_discernibility",  # 品質モデルの切り替え
)

print("levels:", result.levels)            # 選ばれた一般化レベル
print("score:", result.score)              # 解の ILScore(高いほど良い)
print("score function:", result.score_function)
print("k:", result.k, "beta:", result.beta)
print("released:",
      len(result.sampled_indices) - result.suppressed_sample_count,
      "/", len(data))

rows = result.rows  # 出力行(入力と同数。抑制行は全列 "*")
```

主な結果フィールド:

| フィールド | 内容 |
|---|---|
| `levels` | 選ばれた一般化レベル(準識別子の順) |
| `score` / `score_function` | 解の ILScore とその品質モデル(データ依存時のみ。固定スキームでは `None`) |
| `k` / `beta` | SafePub パラメータ |
| `sampled_indices` | サンプルされた行のインデックス |
| `suppressed_sample_count` | k 未満クラスで抑制されたサンプル行数 |
| `non_sampled_count` | サンプル外の行数(出力では抑制) |
| `rows` | 出力行(入力と同数。抑制行は全列 `*`) |
| `utility` / `quality_loss` | 参考用の Precision 情報損失(分析用。SafePub の出力には含まれない) |

## 10. よくある質問

**Q. 実行のたびに結果が変わるのはなぜ?**
A. SafePub はランダムサンプリングと指数メカニズムを使う確率的アルゴリズムだからです。
これは仕様であり、Java版 ARX も同様です。再現が必要な検証では `--deterministic` を使えます。

**Q. ε や δ はどう選べばいい?**
A. δ は「1 ÷ 行数」より小さい値が推奨です(ARX のドキュメントと同じ指針)。
ε を小さくすると k が大きくなり、より強く一般化・抑制されます(プライバシー強・有用性低)。

**Q. 全部の行が `*` になってしまった**
A. データが小さい、または ε が小さすぎて k が行数に近い場合に起こります。
ε を大きくする、データを増やす、階層を粗くする、などを試してください。

**Q. Java版 ARX と完全に同じ結果になる?**
A. アルゴリズムのフロー・式は Java版に合わせていますが、乱数が異なるため個々の実行結果は
一致しません。また Java版は区間演算(保守的な浮動小数点境界)を使うため、境界的なケースで
k や β が 1 段ずれる可能性があります(README の Numerical Note 参照)。
