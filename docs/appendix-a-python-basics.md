# Appendix A: Python 基礎索引（本編で使った文法・記号の早見表）

← [目次](./README.md)

本編に出た Python の記号・キーワード・慣習を、**あとから引く**ための索引です。
「あの記号なんだっけ」となったらここで確認 → 詳しい解剖は該当ステップへ。
既知スタック（TypeScript/React）との対応も併記します。

---

## A-1. 記号・演算子

| 記号 | 読み方 | 意味 | TS/JS での近いもの | 初出 |
|---|---|---|---|---|
| `:` | コロン | ブロック開始（`def`/`class`/`if`/`with` の末尾） | `{` | Step 1 |
| インデント | — | ブロックの中身（スペース4個）。**文法上必須** | `{ }` の中身 | Step 1 |
| `@` | アットマーク | デコレータ（関数を加工/登録） | HOC / メソッドデコレータ | Step 1 |
| `=` | イコール | 代入 | `=` | Step 1 |
| `==` / `!=` | — | 値の等価/不等価 | `===` / `!==` | Step 4 |
| `is` / `is not` | イズ | **同一性**の比較（特に `None` 判定） | `x === null` | Step 3 |
| `[]` | ブラケット | リスト、または添字/キーアクセス | 配列 / `obj[k]` | Step 2 |
| `{}` | ブレース | 辞書(dict) `{k: v}` | オブジェクト | Step 1 |
| `()` | パーレン | 呼び出し / タプル / 複数行の折返し | `()` | Step 1 |
| `,`（末尾） | カンマ | 複数値を並べるとタプル `a, b` | 配列/分割代入に近い | Step 3 |
| `.` (先頭) | ドット | 相対import `from .models` | `./` | Step 2 |
| `*args` | アスター | 可変長**位置**引数を集める/展開する | `...args`（rest/spread） | Step 3 |
| `**kwargs` | ダブルアスター | 可変長**キーワード**引数を集める/展開 | オブジェクトの spread に近い | Step 3 |
| `or` / `and` / `not` | — | 論理演算。`X or Y` は**値**を返す | `\|\|` / `&&` / `!` | Step 3 |
| `A if C else B` | — | 条件式（三項） | `C ? A : B` | Step 3 |
| `f"...{x}..."` | エフ文字列 | 文字列に式を埋め込む | `` `...${x}...` `` | Step 5 |
| `r"..."` | アール文字列 | raw文字列（`\` を特殊扱いしない） | 正規表現リテラル的 | Step 3 |
| `"""..."""` | トリプルクォート | 複数行文字列 / docstring | テンプレートリテラル | Step 1 |
| `__x__` | ダンダー | 特殊属性/変数（`__name__`,`__tablename__`） | 予約的メタ | Step 1 |

---

## A-2. キーワード（予約語）

| キーワード | 意味 | TS/JS | 初出 |
|---|---|---|---|
| `def` | 関数定義 | `function` | Step 1 |
| `class` | クラス定義 | `class` | Step 2 |
| `class X(Y):` | 継承（`Y` が親） | `class X extends Y` | Step 2 |
| `return` | 戻り値 | `return` | Step 1 |
| `import` / `from ... import ...` | モジュール読込 | `import` | Step 1 |
| `as` | 別名 | `import ... as` | Step 3 |
| `if` / `else` | 条件分岐 | 同じ | Step 3 |
| `with ... :` | コンテキスト管理（自動後始末） | `using`（近い）/ try-finally | Step 2 |
| `yield` | 値を返して中断・再開（ジェネレータ） | `yield` | Step 5 |
| `None` / `True` / `False` | 特別値。**先頭大文字** | `null` / `true` / `false` | Step 1 |
| `assert` | 偽なら失敗させる（テスト等） | `console.assert`（用途違い） | Step 5 |

---

## A-3. 命名慣習

| 対象 | 慣習 | 例 | TS/JS との違い |
|---|---|---|---|
| 変数・関数 | **snake_case**（小文字＋`_`） | `create_app`, `user_id` | JS は camelCase |
| クラス | **PascalCase** | `User`, `Post` | 同じ |
| 定数 | **UPPER_SNAKE** | `BASE`, `TEST_DB_URI` | 同じ傾向 |
| テーブル名 | 複数形・小文字 | `users`, `posts` | — |
| 「内部用/使わない」 | 先頭 `_` | `_internal`（本編では未使用） | `#private` に近い意図 |
| 特殊属性 | 前後 `__` | `__name__`, `__tablename__` | — |

> 🧠 Python は「読みやすさは強制」。PEP 8 という公式スタイル指針があり、snake_case もその一部。実務では `ruff`/`black` が自動整形する。

---

## A-4. データ型の対応（ざっくり）

| Python | 例 | TS/JS |
|---|---|---|
| `int` / `float` | `1`, `3.14` | `number` |
| `str` | `"hello"` | `string` |
| `bool` | `True` / `False` | `boolean` |
| `None` | `None` | `null` / `undefined` |
| `list` | `[1, 2, 3]` | 配列 `[]` |
| `dict` | `{"k": 1}` | オブジェクト `{}` |
| `tuple` | `(a, b)` | 固定長配列（不変） |

---

## A-5. よく使う定型（本編で登場したもの）

| やりたいこと | 書き方 | 初出 |
|---|---|---|
| 辞書から安全に取り出す | `data.get("key")`（無ければ `None`） | Step 3 |
| デフォルト付き取り出し | `data.get("key") or 既定` | Step 3 |
| リスト変換（map相当） | `[f(x) for x in xs]` | Step 4 |
| 文字列埋め込み | `f"/posts/{post_id}"` | Step 5 |
| None 判定 | `if x is None:` | Step 3 |
| 複数値を返す | `return body, status` | Step 3 |
| 自動後始末 | `with app.app_context(): ...` | Step 2 |

---

## A-6. uv / Flask / SQLAlchemy コマンド早見

| コマンド | 何をする | 初出 |
|---|---|---|
| `uv init <名前>` | プロジェクト作成 | Step 0 |
| `uv add <pkg>` / `uv add --dev <pkg>` | 依存追加（本番/開発） | Step 0/2 |
| `uv run <cmd>` | 仮想環境内で実行 | Step 0 |
| `uv run flask --app flaskr run` | 開発サーバー起動 | Step 1 |
| `uv run flask --app flaskr init-db` | テーブル作成（自作コマンド） | Step 2 |
| `uv run pytest -v` | テスト実行 | Step 5 |
| `docker compose up -d` / `down` / `down -v` | 起動 / 停止 / ボリュームごと削除 | Step 0/5 |
| `docker compose ps` / `logs -f db` / `exec db mysql ...` | 状態 / ログ / DB接続 | Step 0 |

---

## A-7. SQLAlchemy クエリ早見（新スタイル）

| やりたいこと | 書き方 |
|---|---|
| 主キーで1件 | `db.session.get(User, id)` |
| 条件で1件 | `db.session.scalar(db.select(User).filter_by(username=u))` |
| 条件で複数 | `db.session.scalars(db.select(Post).order_by(Post.created.desc())).all()` |
| 件数 | `db.session.scalar(db.select(db.func.count()).select_from(Post))` |
| 追加 | `db.session.add(obj)` → `db.session.commit()` |
| 更新 | 取得したオブジェクトの属性に代入 → `db.session.commit()` |
| 削除 | `db.session.delete(obj)` → `db.session.commit()` |
| N+1回避 | `db.select(Post).options(db.joinedload(Post.author))` |

---

各項目の「なぜそう動くか」は、初出ステップの `🔬 構文解剖` に詳しく書いています。迷ったらそこへ戻ってください。
