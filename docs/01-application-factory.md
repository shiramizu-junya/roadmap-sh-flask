# Step 1: アプリケーションファクトリ

← [Step 0.5](./00.5-debug-and-query-logs.md) ／ [目次](./README.md) ／ 次: [Step 2](./02-database-sqlalchemy.md)

## 🎯 目的

Flask アプリを **関数の中で組み立てて返す**「アプリケーションファクトリ」を書く。
まず動く `/hello` を1本通して、開発サーバの起動まで確認する。

> **これは核。** ファクトリは「設定・DB・Blueprint をどこで登録するか」の土台で、以降すべてのステップがこの関数に積み上がります。実務の Flask プロジェクトはほぼこの形です。

このステップは **序盤なので完成コードを写経**します。1行ずつ意味を確認しながら書き写してください。

🔁 **置き換え**: 元記事は接続先を `DATABASE`（sqlite ファイルパス）に**直書き**していました。この教材は **MySQL** を使い、接続情報や秘密鍵を **`.env`（環境変数）から読む**形にします。これは「設定をコードに埋め込まない（12-Factor App）」という実務のベストプラクティスで、開発・テスト・本番で接続先を切り替えやすくなります。

---

## 💻 コード

### 1-1. 設定ファイル `.env` を作る

`flaskr-api/` 直下に `.env` を新規作成（**Git 管理外**にする）:

```bash
# DBの接続先（Step0 の docker-compose.yml のユーザー/パスワード/DB名と一致させる）
DATABASE_URL=mysql+pymysql://flaskr:flaskr@localhost:3306/flaskr?charset=utf8mb4
# セッション Cookie の署名に使う秘密鍵（開発用。本番はランダム値に差し替える）
SECRET_KEY=dev
```

- `mysql+pymysql://` … 「MySQL に PyMySQL ドライバで繋ぐ」という意味
- `flaskr:flaskr` … `ユーザー名:パスワード`（compose の `MYSQL_USER`/`MYSQL_PASSWORD`）
- `@localhost:3306/flaskr` … 接続先ホスト:ポート/DB名（compose の `ports` と `MYSQL_DATABASE`）
- `?charset=utf8mb4` … 絵文字も扱える文字コードを指定

> 💡補足: `python-dotenv`（Step0 で `uv add` 済み）が入っていると、`flask` コマンドは**起動時に `.env` を自動で読み込み**、環境変数にセットしてくれます。だから下のコードは `os.environ.get(...)` で値を取れます。

### 1-2. アプリケーションファクトリ

`flaskr/__init__.py` を新規作成:

```python
import os

from flask import Flask


def create_app(test_config: dict | None = None) -> Flask:
    # アプリ本体を生成・設定する「ファクトリ関数」
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # セッション Cookie の署名に使う秘密鍵。.env から読み、無ければ 'dev'
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        # DB 接続先。.env の DATABASE_URL を読む（MySQL に接続する）
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
    )

    if test_config is not None:
        # テスト起動時: 引数で渡された設定で上書き（Step5 で使う）
        app.config.from_mapping(test_config)

    # instance フォルダ（任意の追加設定などを置ける場所）が無ければ作る
    os.makedirs(app.instance_path, exist_ok=True)

    # デバッグ起動時（--debug）だけ、SQL 整形ログを有効化する（Step 0.5 で用意した仕組み）
    if app.debug:
        from . import sql_debug
        sql_debug.enable()

    # 動作確認用の最小ルート
    @app.route("/hello")
    def hello() -> str:
        return "Hello, World!"

    return app
```

---

## 🧠 解説（ブロックごとに「なぜ」）

**① なぜ「グローバルに `app = Flask()`」ではなく関数の中で作るのか**
```python
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
```
グローバルに1個作ると、テスト用と本番用で設定を変えたいときに困ります。
関数（＝ファクトリ）にすると、**呼ぶたびに設定違いのアプリを作れる**（本番用・テスト用）。
- `__name__` … 自分のモジュール名。Flask がファイルの場所を知り、パスを解決するために使う
- `instance_relative_config=True` … 設定ファイルや DB を、Git 管理しない `instance/` フォルダ基準にする

> 🔗 **React との接続**: `create_app()` は React で言う「Provider を組んだ `<App>` を返すファクトリ関数」に近い。副作用を関数内に閉じ込め、外から設定を注入できる形にしている、という発想は同じです。

**② 設定を「環境変数 → 引数で上書き」の二段で入れる**
```python
app.config.from_mapping(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
)
if test_config is not None:
    app.config.from_mapping(test_config)
```
- `SECRET_KEY` … Flask がセッション Cookie を**署名**（改ざん検知）するのに使う。Step3 のログインで効いてくる
- `SQLALCHEMY_DATABASE_URI` … 🔁 **置き換え**: 元記事は `DATABASE`（sqlite ファイルパス）を直書きでした。ここでは **`.env` の `DATABASE_URL`（MySQL 接続 URI）** を読みます。接続先をコードに埋め込まないので、テストや本番で差し替えやすい
- `test_config` を受け取れるのは、Step5 のテストで**本番と別の DB（`flaskr_test`）を渡す**ため

> 💡補足: `os.environ.get("DATABASE_URL")` が `None` になる（＝`.env` が読まれていない）と DB 接続で失敗します。`.env` が `flaskr-api/` 直下にあり、`python-dotenv` が入っているか確認してください。

**③ instance フォルダを作る**
```python
os.makedirs(app.instance_path, exist_ok=True)
```
Flask は `instance/` を自動作成しません。任意の追加設定を置ける場所として確保しておきます（MySQL を使うので、元記事のように DB ファイルを置く用途ではありません）。

**④ SQL 整形ログを有効化する（デバッグ時のみ）**
```python
if app.debug:
    from . import sql_debug
    sql_debug.enable()
```
[Step 0.5](./00.5-debug-and-query-logs.md) で作った `flaskr/sql_debug.py` を、`--debug` 起動時だけ有効化します。これで Step 2 以降、アプリが発行する SQL が**整形＋実行時間つき**でターミナルに流れ、「今どんなクエリが走ったか」を観測しながら開発できます。`app.debug` ガードにより、テストや本番では静かなままです。

> ⚠️ `flaskr/sql_debug.py` が無いと `ImportError` になります。先に [Step 0.5](./00.5-debug-and-query-logs.md) を済ませてください（まだなら、この `if app.debug:` ブロックを一旦コメントアウトして進めてもOK）。

**④ 動作確認用ルート**
```python
@app.route("/hello")
def hello():
    return "Hello, World!"
```
`@app.route("/hello")` は「URL `/hello` へのリクエストをこの関数で処理する」宣言。
関数の戻り値がそのままレスポンスになります。

---

## 🔮 予測 → 動作確認

**実行する前に予想してみよう。** 次の観点で考えてください。
- `flask --app flaskr run --debug` は何を起動する？
- ブラウザで `/hello` を開くと何が返る？ `/` を開いたら？

実行:
```bash
# flaskr-api/ ディレクトリで（uv run が自動で仮想環境を使う。activate 不要）
uv run flask --app flaskr run --debug
```

> 💡補足: `uv run` を付けるのが、この教材の全 `flask`/`pytest` コマンド共通のポイントです。素の `flask ...` だと「コマンドが無い」と言われます。

期待される起動ログ:
```
 * Serving Flask app 'flaskr'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

別ターミナル（または別タブ）で:
```bash
curl http://127.0.0.1:5000/hello
```
期待される出力:
```
Hello, World!
```

- `/hello` … `Hello, World!`（上のとおり）
- `/`（ルート）… まだ定義していないので **404 Not Found**。これは正常です（Step4 で `/posts` などを足していく）

> 💡補足: `--debug` はデバッグモード。例外が出たら詳細画面が出て、コードを保存すると自動で再起動します。開発中は付けっぱなしでOK。

---

## ✅ 想起チェック

**見ないで説明してみよう:** 「アプリケーションファクトリ」とは何で、グローバルに `app` を作るのと比べて何が嬉しいか、を口頭で説明できますか？

<details><summary>解答例</summary>

`create_app()` のように **アプリの生成・設定・登録を関数の中で行い、完成した `app` を返す**設計。
グローバルに1個作る方式と違い、**呼び出しごとに設定違いのアプリを生成できる**ため、テスト用（別 DB・`TESTING=True`）と本番用を作り分けられ、循環 import も避けやすい。以降の設定・DB・Blueprint 登録はすべてこの関数の中に集約する。
</details>

**小問:** 元記事の設定キー `DATABASE`（sqlite3 用のファイルパス）を、この教材では何というキーに置き換えた？ なぜ？

<details><summary>解答例</summary>

`SQLALCHEMY_DATABASE_URI` に置き換えた。生 sqlite3 の代わりに **Flask-SQLAlchemy** を使うため。SQLAlchemy は接続先を `sqlite:///<パス>` という **URI 文字列**で受け取るので、キー名と値の形式が変わる。
</details>

---

次は [Step 2: SQLAlchemy でモデルと DB 初期化](./02-database-sqlalchemy.md)。
