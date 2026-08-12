# Step 1: アプリケーションファクトリで Flask を組み立てる

← [Step 0](./00-env.md) ／ [目次](./README.md) ／ 次: [Step 2](./02-database-sqlalchemy.md)

**作るもの**: `create_app()` という関数で Flask アプリを組み立て、最初の REST ルート `GET /health` を JSON で返す
**重要度**: 🔴 **毎日書く**（Flask アプリの起点。実務のFlaskはほぼ全部この形）
**前ステップとの接続**: Step 0 で作った `flaskr-api/` の中に、Flask アプリ本体 `flaskr` パッケージを作る

---

## 1-1. まず動くものを作る（コード全文・写経）

`flaskr-api/` の中に、次の構成でファイルを作ります。

```
flaskr-api/
├─ docker-compose.yml     ← Step 0 で作成済み
├─ pyproject.toml         ← uv が管理
└─ flaskr/                ← ★これから作る「アプリ本体」パッケージ
   └─ __init__.py         ← ★このファイルにファクトリを書く
```

**ファイル: `flaskr-api/flaskr/__init__.py`（全文）**

```python
from flask import Flask


def create_app():
    """Flask アプリを組み立てて返すファクトリ関数。"""
    app = Flask(__name__)

    # 設定（今は最小限。あとで DB 接続などをここに足す）
    app.config["SECRET_KEY"] = "dev"  # 開発用。本番では環境変数から読む

    # 動作確認用のルート（あとで本物の API に置き換える）
    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
```

これだけで REST API サーバーが1本立ちます。まず**なぜこの文字列でこう動くのか**を分解します。

---

## 1-2. 🔬 構文解剖

### 🔬 構文解剖: `from flask import Flask`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `from` | フロム | 「どのモジュールから」を指定する import 構文の始まり |
| `flask` | — | インストール済みライブラリ（パッケージ）名 |
| `import` | インポート | 読み込む |
| `Flask` | — | `flask` パッケージの中の `Flask` クラスを、この名前で使えるようにする |

**既知スタックとの対応**: `import { Flask } from "flask"`（TS の名前付きインポート）とほぼ同じ。
`from A import B` = 「A から B を取り出す」。`import flask` だけなら `flask.Flask` と毎回書くことになる。
**なぜこの書き方か**: よく使うものは `from ... import ...` で直接名前を取り込むのが Python の慣習。

### 🔬 構文解剖: `def create_app():`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `def` | デフ | **関数を定義**するキーワード（define）。JS の `function` に相当 |
| `create_app` | — | 関数名。**スネークケース**（小文字＋`_`）が Python の関数名の慣習 |
| `()` | — | 引数リスト。今は引数なし |
| `:` | コロン | **ブロックの始まり**を示す。この後の**インデントされた行**が関数の中身 |
| （インデント） | — | Python は `{}` ではなく**字下げでブロックを表す**。半角スペース4個が標準 |

**既知スタックとの対応**: `function createApp() { ... }`。中括弧 `{}` の代わりに `:` とインデントで body を表すのが Python。
**なぜインデントか**: Python は「見た目の字下げ＝構造」。だから**インデントを間違えると意味が変わる**（TSの整形と違い、必須の文法）。

> 🧠 **この言語の考え方**: Python は「読みやすさは強制する」。ブロックを波括弧ではなくインデントで表すのはその思想の表れ。

### 🔬 構文解剖: `"""Flask アプリを...返すファクトリ関数。"""`（docstring）

| 部品 | 読み方 | 意味 |
|---|---|---|
| `"""..."""` | トリプルクォート | 三連ダブルクォートの文字列。複数行書ける |
| 関数の**先頭行**に置く | — | **docstring**（ドックストリング）。その関数の説明として特別に扱われる |

**既知スタックとの対応**: JSDoc コメント（`/** ... */`）に近いが、こちらは**コメントではなく文字列**で、実行時に `help()` などから読める。
**なぜ使うか**: 関数の意図を先頭に1行で残すのは実務の基本。省略も可能だが、この教材では最初から付ける。

### 🔬 構文解剖: `app = Flask(__name__)`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `app = ...` | — | 変数 `app` に代入。Python は型宣言なしで代入できる（動的型付け） |
| `Flask(...)` | — | `Flask` クラスを**呼び出してインスタンスを作る**。JS と違い `new` は不要 |
| `__name__` | ダンダーネーム | Python が自動で用意する特殊変数。「今実行中のモジュール名」が入る |

**`__name__` とは**: `__` で挟まれた名前は **dunder**（double underscore）と呼ぶ特殊なもの。
`__name__` には、そのファイルがどう呼ばれたかに応じて文字列が入る（パッケージ名など）。Flask はこれを使って「アプリの基準となる場所（テンプレートや静的ファイルを探す起点）」を決める。
**既知スタックとの対応**: `new Flask(...)` の `new` 不要版。`__name__` に直接の対応物はない（Python 特有）。
**なぜ渡すか**: Flask に「自分がどこにいるか」を教えるため。定型句としてこう書く（ただし理由は上記の通り明確）。

### 🔬 構文解剖: `app.config["SECRET_KEY"] = "dev"`

| 部品 | 意味 |
|---|---|
| `app.config` | Flask の設定を入れる**辞書（dict）風オブジェクト** |
| `["SECRET_KEY"]` | 角カッコでキー指定。`辞書[キー] = 値` で設定を書き込む |
| `"SECRET_KEY"` | Flask が決めているキー名。セッション Cookie の署名に使う秘密の値 |

**既知スタックとの対応**: JS のオブジェクト `obj["key"] = value` と同じ書き方。`config` はほぼ Map/オブジェクト。
**なぜ SECRET_KEY か**: Step 3 のセッション認証で Cookie を暗号署名するのに必要。今は開発用に `"dev"` を置く。
**⚪ 背景**: 本番でこれがバレると Cookie を偽造される。だから本番は環境変数から読む（後のステップで直す）。

### 🔬 構文解剖: `@app.get("/health")`（デコレータ）

| 部品 | 読み方 | 意味 |
|---|---|---|
| `@` | アットマーク | **デコレータ**構文。直後に定義した関数を、`@` の後ろの関数に渡して機能を足す |
| `app.get(...)` | — | `app` の `get` メソッド呼び出し。「`GET /health` が来たら次の関数を呼べ」と登録する |
| `"/health"` | — | URL パス（位置引数） |

**デコレータとは**: `@app.get("/health")` は「**次に書く関数 `health` を、ルーティング表に登録する**」という意味。
`health` 関数はそのまま定義されつつ、「`GET /health` のハンドラ」として Flask に覚えられる。
**既知スタックとの対応**: React の HOC（`withRouter(Component)`）や、Express の `app.get("/health", handler)` と同じ発想。
Express は「パスとハンドラを引数で並べる」が、Flask は「関数の**上に** `@` で宣言的に貼る」。URL とハンドラが隣接して読みやすい。
**なぜ `.get` か**: HTTP メソッドごとに `@app.get` / `@app.post` / `@app.put` / `@app.delete` がある。REST では動詞をメソッドで表すので、メソッド別デコレータが素直。

> 💡 **補足**: 古い Flask 記事では `@app.route("/health", methods=["GET"])` と書く。
> `@app.get("/health")` はその短縮形（Flask 2.0+）。この教材は新しい方に統一する。

### 🔬 構文解剖: `return {"status": "ok"}`

| 部品 | 意味 |
|---|---|
| `return` | 関数の戻り値を返す（JS と同じ） |
| `{"status": "ok"}` | **辞書（dict）**。`{キー: 値}`。JS のオブジェクトリテラルとほぼ同じ見た目 |

**Flask の重要な仕様**: ハンドラが**辞書を返すと、Flask は自動で JSON に変換**し、`Content-Type: application/json` を付けて返す。
だから REST API では「辞書を return するだけ」で JSON レスポンスになる。
**既知スタックとの対応**: Express の `res.json({ status: "ok" })` を、`return` するだけで済ませられる。
**なぜこれで十分か**: この教材は JSON を返す API なので、`return 辞書` が基本形。HTML(`render_template`)は使わない（🔁 置き換え：公式の Jinja を JSON に置換）。

---

## 1-3. 解説 — なぜ「ファクトリ関数」にするのか

`app = Flask(__name__)` をファイルの一番外（グローバル）に書いてしまう書き方もあります。
でもこの教材は**必ず `create_app()` 関数の中で組み立てて `return` する**（＝アプリケーションファクトリ, application factory）。理由は3つ。

1. **テストしやすい**: テストのたびに「新しいアプリ」を関数呼び出しで作れる。設定違い（本番用/テスト用DB）のアプリを作り分けられる
2. **設定を引数で差し替えられる**: 後で `create_app(test_config)` のように設定を注入できる
3. **循環インポートを避けられる**: DBや各機能を後から `app` に登録する順番を制御できる（Step 2 以降で効いてくる）

> 🧠 **この言語（Flask）の考え方**: 「アプリはグローバル変数ではなく、関数が組み立てて返す“成果物”」。
> React でいう「巨大なグローバル state を持たず、必要な時に factory / provider で作る」に近い設計思想。

> 🔁 **置き換え**: 公式チュートリアルも `create_app()` を採用している。この点は公式と同じ。
> ただし公式は中で `sqlite3` を設定するが、この教材では Step 2 で **SQLAlchemy + MySQL** を登録する。

---

## 1-4. 🏢 実務メモ / ⚠️ アンチパターン

### 🏢 実務メモ
`create_app()` は「**登録だけ**する場所」に保つのが実務の定石。
具体的なDBクエリやビジネスロジックはここに書かず、後で作る **Blueprint（機能ごとのルート束）** に分ける。`create_app` は「拡張(DB/CORS等)の初期化」と「Blueprint の登録」だけを並べる薄い関数にする。

> ⏭️ **後で回収**: **Blueprint**（`auth` や `posts` のようにルートを機能ごとに分割する仕組み）は **Step 3** で導入する。
> 今は「`create_app` の中にルートを直書きしている状態」で問題ない。Step 3 で機能別ファイルに切り出す。

### ⚠️ やりがち
> **やりがち**: ハンドラ関数（`health` など）を `create_app` の**外**（グローバル）に書いて `app` を参照しようとし、`app` が未定義でエラーになる。
> **現場では**: 直書き段階ではハンドラは `create_app` の**内側**に置く。規模が大きくなったら Blueprint に分けて外に出す（Step 3）。

---

## 1-5. 🔮 予測 → 動作確認

### まず Flask を確実に入れておく

```bash
# flaskr-api/ の中で（Step 0 で入れていなければ）
uv add flask
```

### 🔮 実行前に予想しよう
次の3つを予想してから実行してください。

1. `GET /health` に対して**ステータスコード**は何番が返る？
2. レスポンスの**ボディ**はどんな文字列？
3. レスポンスの `Content-Type` ヘッダは何になる？

### 起動する（通常起動）

```bash
# flaskr-api/ の中で
uv run flask --app flaskr run --port 5000
```

### 🔬 構文解剖: `uv run flask --app flaskr run --port 5000`

| 部品 | 意味 |
|---|---|
| `uv run` | 仮想環境の中で実行（Step 0 参照） |
| `flask` | Flask の CLI |
| `--app flaskr` | 「アプリは `flaskr` パッケージ」と教える。Flask は `flaskr/__init__.py` の `create_app()` を自動で探して呼ぶ |
| `run` | 開発サーバーを起動するサブコマンド |
| `--port 5000` | 待ち受けポート。省略時も 5000 |

**なぜ `--app flaskr` でファクトリが見つかるか**: Flask は指定パッケージの中に `create_app()` または `create_app(...)` があれば、それをファクトリとみなして自動で呼ぶ。だから明示指定は不要。

### 動作確認

別のターミナルで:

```bash
curl -i http://127.0.0.1:5000/health
```

### 期待される出力

```
HTTP/1.1 200 OK
Content-Type: application/json
...
{"status":"ok"}
```

- ステータス **200**（予想1の答え）
- ボディ **`{"status":"ok"}`**（予想2の答え。辞書が自動で JSON 化された）
- Content-Type **application/json**（予想3の答え。辞書 return で自動付与）

`-i` はレスポンスヘッダも表示するオプション。ステータスと Content-Type を確認するために付けています。

### （任意）Step 0 のデバッグ起動を今すぐ試す

Step 0 で用意した attach デバッグを、この最小アプリで試せます。

```bash
# iTerm2 で
uv run python -m debugpy --listen 5678 --wait-for-client -m flask --app flaskr run --no-reload
```

`health` 関数の `return {"status": "ok"}` の行に Zed でブレークポイントを張り、`debugger: start` でアタッチ → `curl http://127.0.0.1:5000/health` を叩くと、その行で止まります（詳細な手順は [Step 0 の 0-5-5](./00-env.md)）。

---

## 1-6. ✅ 想起チェック

<details><summary>Q1. `@app.get("/health")` の `@` は何をしている？</summary>

デコレータ。直後に定義した `health` 関数を Flask のルーティング表に「`GET /health` のハンドラ」として登録する。関数自体はそのまま使えるまま、機能（ルート登録）が足される。
</details>

<details><summary>Q2. ハンドラが `return {"status": "ok"}` すると、なぜ JSON が返る？</summary>

Flask はハンドラが辞書(dict)を返すと自動で JSON にシリアライズし、`Content-Type: application/json` を付ける仕様だから。`res.json(...)` を明示的に呼ばなくてよい。
</details>

<details><summary>Q3. なぜアプリをグローバルに置かず `create_app()` 関数で作るのか（1つ挙げよ）</summary>

テストで新しいアプリを作り分けられる／設定を引数で差し替えられる／登録順を制御して循環インポートを避けられる、のいずれか。
</details>

<details><summary>Q4. `def` の後ろの `:` と行頭のインデントは何を表す？</summary>

`:` はブロックの開始、インデント（スペース4個）はそのブロックの中身。Python は `{}` ではなくインデントでブロック構造を表す。字下げを間違えると意味が変わる。
</details>

---

## まとめ

- Flask アプリは **`create_app()` ファクトリ**で組み立てて `return` する
- ルートは **`@app.get("/path")`** デコレータで関数に貼る
- ハンドラが**辞書を return すると自動で JSON** になる（REST API の基本形）
- 起動は **`uv run flask --app flaskr run`**

次の [Step 2](./02-database-sqlalchemy.md) で、この `create_app` に **SQLAlchemy** を登録し、Docker の **MySQL** に接続してテーブルを作ります。
