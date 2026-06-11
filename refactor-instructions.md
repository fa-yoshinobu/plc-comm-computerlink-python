# refactor-instructions.md

plc-comm-computerlink-python のリファクタリング指示書。
この文書は実装担当モデル向けの完結した作業指示である。実装前にこの文書全体を読むこと。

> **最重要の前提**: このパッケージは PyPI に公開済み(`toyopuc-computerlink` 0.1.8)であり、
> JTEKT TOYOPUC Computer Link の実装は実機検証記録(`TODO.md`、`internal_docs/`)に紐づく。
> **公開 API・送信フレームのバイト列を変えてはならない。**
>
> 本リポジトリには `scripts/sim_server.py`(PLC シミュレータ)と CI のシミュレータ
> スモークという**他リポジトリより強い安全網**が既にある。本タスクの中心は
> **`high_level.py`(2,008 行)の内部分割**であり、シミュレータがその検証手段になる。

---

## Objective

公開 API・ワイヤバイト列・.NET 版との意味的互換を一切壊さずに:

1. **`toyopuc/high_level.py`(2,008 行)のモジュール内責務を move-only で分割する**
   (アドレス解決 / PC10 パッキング / バッチ計画 / `ToyopucDeviceClient` 本体)
2. 分割した純粋ロジックに**直接のユニットテストを追加する**
3. `toyopuc.high_level` の既存公開名は**すべて再エクスポートで不変に保つ**

---

## Project Understanding

### 何のライブラリか

JTEKT TOYOPUC PLC と Computer Link(イーサネット TCP/UDP)で通信する Python ライブラリ。
中継局ホップ、FR 書込 + Commit、PC10 モード、機種別プロファイル対応。
.NET 版(`plc-comm-computerlink-dotnet`)と高レベル契約(`open_and_connect` /
`read_typed` / `write_typed` / `read_named` / `poll`)を共有(`TODO.md` の Cross-Stack 節)。

### モジュール構成(toyopuc/、計約 5,300 行)

| ファイル | 行数 | 内容 |
|---|---|---|
| `high_level.py` | 2,008 | デバイス解決(`resolve_device` 309 行〜)、PC10 マルチビット/ワードのパッキング(534〜600 行)、バッチ計画(`_batch_run_length` 638 行〜)、`ToyopucDeviceClient`(695 行〜) |
| `profiles.py` | 969 | 機種プロファイル(データ主体。触らない) |
| `client.py` | 958 | 低レベル同期 `ToyopucClient`(トランスポート + コマンド) |
| `utils.py` | 492 | 契約ヘルパ(`read_typed` / `poll` 等) |
| `address.py` / `protocol.py` / `relay.py` | 1,047 | アドレス解析・フレーム組立・中継(純粋。健全) |
| `async_client.py` | 159 | thin async ラッパ(健全) |

### テスト / CI / 検証コマンド

- `tests/` の pytest スイート
- `run_ci.bat`: ruff check → ruff format --check → mypy toyopuc →
  scripts/samples の py_compile → pytest → **sim_server 起動 + スモーク**
  (`scripts/run_sim_tests.bat`)→ PyInstaller(`scripts/interactive_cli.py`)
- `scripts/` の大物(`auto_rw_test.py` 1,796 行 / `interactive_cli.py` 等)は
  実機検証・保守ツール。**触らない**(py_compile が通ることのみ維持)。

---

## Behaviors To Preserve(絶対に壊さない既存挙動)

1. **公開 API**: `toyopuc/__init__.py` の export 一覧と、`toyopuc.high_level` /
   `toyopuc.utils` 等のモジュールパス + その中の既存公開名(`resolve_device` /
   `ResolvedDevice` / `ToyopucDeviceClient` を含む)。
2. **送信フレームのバイト列**: パッキング関数群の出力。
3. **バッチ計画の分割規則**: PC10 ブロック境界、連続判定、FR の特別扱い
   (`_raise_generic_fr_write_error`)。
4. **プロファイル検証**(`_validate_profile_access`)の拒否条件と例外文言。
5. **セマンティック原子性**(TODO.md): FR / PC10 ブロック境界以外での暗黙分割禁止。
6. **依存・バージョン**: `pyproject.toml` 変更禁止。0.1.8 のまま。
7. **UDP 応答の截断回避修正**(commit `91f2b5b`)等、直近の修正挙動。

---

## Non-Negotiables(交渉不可の制約)

- 最初に `git status` を確認する。未コミット変更があれば混ぜず、報告して停止する。
- 編集前に Baseline Commands をすべて実行し、結果(テスト件数含む)を記録する。
- 変更は小さく戻しやすい単位。コミットはユーザーの指示があるまで行わない。
- 無関係な整形・「ついで」リファクタリングをしない。
- 依存を追加しない。`pyproject.toml` / `toyopuc.spec` を変更しない。
- 分割先は非公開モジュール(例: `toyopuc/_pc10.py` / `toyopuc/_batching.py`)とし、
  `high_level.py` から**同名で再インポート**して後方互換を保つ
  (`from toyopuc.high_level import _read_pc10_multi_bits` のような既存の内部参照が
  scripts/tests に無いか grep で確認してから移動する)。
- 既存テストの既存アサーションを変更しない(追加のみ可)。
- 実機 PLC への接続を行わない(シミュレータは可)。
- 正しさが不明な場合は実装を止め、「Stop And Ask」として質問を報告書に書く。

---

## Stop And Ask Conditions(即時停止して質問する条件)

- 移動対象の関数がモジュールグローバルな状態・インポート順序に依存していた
- 特性テスト作成中に、パッキング出力やバッチ分割結果が .NET 版・文書と食い違って見えた
  (**修正せず**報告)
- 既存テスト・シミュレータスモークが自分の変更後に落ちた ⇒ 即座に巻き戻して報告
- 公開名・例外文言・フレームバイト列に影響しうる変更が必要に見えた
- 本書の Debt Map に無い大きな問題を発見した(報告のみ)

---

## Baseline Commands

作業ディレクトリ: リポジトリルート。Python 3.10+。Windows 前提(`run_ci.bat`)。
実機 PLC 不要・接続禁止。

```bat
git status                                  & rem クリーンであることを確認
python -m ruff check toyopuc tests scripts samples
python -m ruff format --check toyopuc tests scripts samples
python -m mypy toyopuc
python -m pytest tests                      & rem テスト件数を記録
```

シミュレータスモーク(推奨。`run_ci.bat` 第 6 ステップ相当):

```bat
rem 別プロセスで: python scripts\sim_server.py --host 127.0.0.1 --port 15000
call scripts\run_sim_tests.bat 127.0.0.1 15000 tcp
```

PyInstaller は環境にあれば実行、無ければ未実施と報告書に明記。

---

## Debt Map

行番号は調査時点(main, commit `91f2b5b`)のアンカー。ドリフトしていたら宣言名で探すこと。

### D1. 純粋ロジックの特性テスト不足 【実装可 / 最優先】

- **根拠**: `_pack_pc10_multi_bit_payload` / `_pack_pc10_multi_word_payload` /
  `_build_pc10_multi_word_read_payload` / `_batch_run_length` / `_is_consecutive_*` 等は
  純粋関数だが、直接のユニットテストが薄い(クライアント/シミュレータ経由が主)。
- **改善案**: 代表入力(単独、連続、PC10 ブロック境界跨ぎ、FR、ビット/ワード混在)の
  現在出力を採取し、特性テストを `tests/` に追加。期待値は現在の実装出力に限る。
- **リスク**: 低。

### D2. `high_level.py`(2,008 行)の責務同居 【実装可 / 主作業】

- **根拠**: (a) アドレス→物理解決(`_infer_unit_and_area` / `resolve_device`)、
  (b) PC10 パッキング(534〜600 行)、(c) バッチ計画(624〜695 行)、
  (d) `ToyopucDeviceClient`(695 行〜末尾、約 1,300 行)が 1 モジュールに同居。
- **なぜ負債か**: (b)(c) は最も複雑な純粋ロジックで .NET 版との対応確認が頻繁に必要だが、
  巨大モジュール内に埋もれている。
- **改善案**: move-only で非公開モジュールへ:
  - `toyopuc/_pc10.py`: (b) パッキング/パース系
  - `toyopuc/_batching.py`: (c) 計画系
  - `high_level.py` には**同名の再インポートを残す**(内部参照・テスト互換)
  - (a)(d) は `high_level.py` に残す(公開面のため移動しない)
- **影響範囲**: toyopuc パッケージ内。公開 API 不変。
- **リスク**: 中。D1 完了後に着手。
- **検証**: pytest + シミュレータスモーク。

### D3. `utils.py` と `high_level.py` の役割境界 【現状維持 / 報告のみ】

- 契約ヘルパが `utils.py`、デバイスクライアントが `high_level.py` という配置は
  .NET 版(Extensions / DeviceClient)との対応であり、rename は公開面の変更になる。
  触らない。

### D4. `scripts/auto_rw_test.py`(1,796 行)等の保守ツール肥大 【現状維持 / 報告のみ】

- 実機検証ツールでありライブラリ品質に直接影響しない。py_compile が通る状態を維持するのみ。

---

## Implementation Phases

### Phase 0: 現状確認

1. `git status` 確認(クリーンでなければ停止・報告)
2. Baseline Commands(シミュレータスモーク含む)を実行し、結果を記録

### Phase 1: 特性テスト(D1)

1. パッキング系・計画系の特性テストを追加(期待値は現在出力の採取)
2. 全テスト実行

### Phase 2: 内部分割(D2)

1. 移動前に `_pc10` / `_batching` 対象関数の参照箇所を grep
   (`toyopuc/` / `tests/` / `scripts/` / `samples/`)し、参照リストを記録
2. `_pc10.py` 分離 → pytest + スモーク → `_batching.py` 分離 → pytest + スモーク
3. 想定外の依存が出たらその関数をスキップして報告

### Phase 3: 検証と報告

1. 全 Verification Requirements を最終実行
2. Reporting Format に従って報告書を作成

---

## Verification Requirements

各フェーズ完了時に最低限:

```bat
python -m ruff check toyopuc tests scripts samples
python -m ruff format --check toyopuc tests scripts samples
python -m mypy toyopuc
python -m pytest tests
```

最終フェーズでは追加で:

- シミュレータスモーク(`run_sim_tests.bat`)が通ること
- テスト件数が baseline から増えていること
- `git diff` で確認: `toyopuc/__init__.py` 無変更、`pyproject.toml` /
  `toyopuc.spec` / `CHANGELOG.md` 無変更、`scripts/` / `samples/` 無変更
- `python -c "from toyopuc.high_level import resolve_device, ToyopucDeviceClient"` が通ること

---

## Reporting Format

1. **Baseline 結果**: 実行コマンドと結果(テスト件数、スモーク結果)
2. **特性テスト一覧**: 対象関数 × 入力ケース
3. **移動一覧**: 関数 × 移動先 × 参照箇所の確認結果
4. **各フェーズの検証結果**: 最後に実行したコマンドと結果(失敗を隠さない)
5. **Stop And Ask**: 発生した質問と停止範囲
6. **未実施事項**: PyInstaller 未実施等の明記

---

## Out-of-scope Items(やらないこと)

- 公開 API・モジュールパス・公開名の変更/追加/整理
- 送信フレームバイト列・バッチ分割規則・例外文言の変更
- `profiles.py`(実機検証に紐づくデータ)/ `protocol.py` / `address.py` の変更
- `scripts/` / `samples/` の変更(py_compile 維持のみ)
- sync/async 構造の変更(`async_client.py` は thin ラッパのまま)
- バージョン変更、`CHANGELOG.md` 更新、PyPI 公開
- 依存追加、`pyproject.toml` / spec 変更、CI 変更
- 実機 PLC を使う検証
- 兄弟リポジトリ(dotnet 版ほか)の変更
