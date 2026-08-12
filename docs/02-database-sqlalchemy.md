# Step 2: SQLAlchemy でモデルを定義し MySQL につなぐ

← [Step 1](./01-application-factory.md) ／ [目次](./README.md) ／ 次: Step 3（準備中）

**作るもの**: SQLAlchemy を `create_app` に登録し、`User`（ユーザー）と `Post`（記事）のテーブルを Docker の MySQL に作る
**重要度**: 🔴 **毎日書く**（DBアクセスは全機能の土台。モデル定義は毎回書く）
**前ステップとの接続**: Step 1 の `create_app()` に、DB拡張の初期化を1ブロック足す

> 🔁 **置き換え**: 公式チュートリアルは生 `sqlite3` に `schema.sql` を流し込む。
> この教材では **Flask-SQLAlchemy（ORM）** で **MySQL**（Step 0 の Docker）に接続する。
> 「SQL文字列を手で書く」代わりに「Python のクラスでテーブルを表す」方式に置き換える。

---

## 2-1. 使うライブラリを入れる

```bash
# flaskr-api/ の中で
uv add flask-sqlalchemy pymysql
```

| ライブラリ | 役割 |
|---|---|
| `flask-sqlalchemy` | Flask から SQLAlchemy(ORM) を使うための統合パッケージ |
| `pymysql` | Python から MySQL に接続する**ドライバ**（純Python製で導入が楽） |

> 💡 **補足（ドライバとは）**: ORM(SQLAlchemy)は「どう組み立てるか」を担うが、実際に MySQL と通信する部品が別に要る。それがドライバ(`pymysql`)。
> 接続文字列で `mysql+pymysql://...` と書くと「MySQL に pymysql ドライバで繋ぐ」の意味になる（後述）。

---

## 2-2. モデルを定義する（コード全文・写経）

まず「DB拡張オブジェクト」と「モデル」を置くファイルを作ります。

```
flaskr-api/flaskr/
├─ __init__.py     ← Step 1 で作成。今回ここに DB 登録を足す
└─ models.py       ← ★新規。db オブジェクトとモデルを書く
```

**ファイル: `flaskr-api/flaskr/models.py`（全文）**

```python
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# DB拡張のインスタンス。まだアプリには結び付いていない（後で init_app で結ぶ）
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # このユーザーが書いた記事たち（1対多のリレーション）
    posts = db.relationship("Post", back_populates="author")


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", back_populates="posts")
```

---

## 2-3. 🔬 構文解剖

### 🔬 構文解剖: `from datetime import datetime`

| 部品 | 意味 |
|---|---|
| `datetime`（前） | 標準ライブラリの**モジュール名** |
| `datetime`（後） | そのモジュールの中の**クラス名**（同名でまぎらわしいが別物） |

つまり「`datetime` モジュールから `datetime` クラスを取り出す」。以降 `datetime.utcnow` のように使える。
**既知スタックとの対応**: JS の `Date` に相当するクラスを import している。

### 🔬 構文解剖: `db = SQLAlchemy()`

| 部品 | 意味 |
|---|---|
| `SQLAlchemy()` | 拡張クラスを呼んでインスタンス化。**まだ特定のアプリには結び付いていない** |
| `db` | これ以降、モデル定義(`db.Model`)やDB操作(`db.session`)の入口になるオブジェクト |

**なぜアプリの外で作るか**: `db` をグローバルに1個作り、後で `db.init_app(app)` でアプリに結ぶ。
こうすると `models.py`（モデル定義）と `__init__.py`（アプリ組み立て）を分離でき、循環インポートを避けられる。Step 1 で触れたファクトリの利点がここで効く。
**既知スタックとの対応**: 「シングルトンの拡張インスタンスを作って後で初期化する」パターン。ORM を1箇所に集約する点は Prisma Client を1つ作って使い回すのに近い。

### 🔬 構文解剖: `class User(db.Model):`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `class` | クラス | クラスを定義するキーワード |
| `User` | — | クラス名。**パスカルケース**（先頭大文字）が Python のクラス名の慣習 |
| `(db.Model)` | — | **継承**。カッコ内の `db.Model` を親クラスにする。JS の `extends db.Model` に相当 |
| `:` | — | ブロック開始。以降インデントした行がクラスの中身 |

**`db.Model` を継承する意味**: `db.Model` を親にすると、そのクラスは「1つのDBテーブルを表すモデル」になる。
SQLAlchemy がクラス定義を読み取り、テーブルと列を対応付ける（これを **ORM = Object-Relational Mapping** と呼ぶ）。
**既知スタックとの対応**: `class User extends Model`。Prisma の `model User { ... }` 宣言に相当するが、Python では**クラス**で表す。

### 🔬 構文解剖: `__tablename__ = "users"`

| 部品 | 意味 |
|---|---|
| `__tablename__` | dunder（`__ __`）の特殊属性。SQLAlchemy が「このモデルのテーブル名」として読む |
| `"users"` | 実際のテーブル名。慣習として**複数形・小文字** |

**なぜ明示するか**: 省略すると SQLAlchemy がクラス名から自動命名するが、規則が分かりにくい。実務では**明示して複数形**にするのが読みやすい。
**既知スタックとの対応**: Prisma の `@@map("users")` に近い。

### 🔬 構文解剖: `id = db.Column(db.Integer, primary_key=True)`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `id = ...` | — | クラス直下に書く**クラス属性**。これ1つが1つの**カラム（列）**になる |
| `db.Column(...)` | カラム | 列を定義する関数 |
| `db.Integer` | — | 列の**型**。整数。第1引数（位置引数） |
| `primary_key=True` | — | **キーワード引数**。`名前=値` で渡す。「この列を主キーにする」 |
| `True` | トゥルー | Python の真偽値。**先頭大文字**（`true` ではない） |

**キーワード引数とは**: `primary_key=True` のように `名前=値` で渡す引数。位置に依存せず、何を指定しているか読んで分かる。
**既知スタックとの対応**: 型付きの列宣言。Prisma の `id Int @id`、TypeORM の `@PrimaryGeneratedColumn()` に相当。
**なぜ主キーを整数の id にするか**: 各行を一意に識別する列が要る。整数の自動採番が最も素直（MySQL では `AUTO_INCREMENT` になる）。

### 🔬 構文解剖: 各カラムのオプション

```python
username = db.Column(db.String(80), unique=True, nullable=False)
```

| 部品 | 意味 |
|---|---|
| `db.String(80)` | 可変長文字列。**最大80文字**。MySQL の `VARCHAR(80)` になる |
| `unique=True` | この列は**重複禁止**（同じ username を2人持てない） |
| `nullable=False` | **NULL 禁止**＝必須列。空では保存できない |
| `db.Text` | 長い文章用の型（`body` で使用）。`String` と違い長さ上限を実質気にしない |
| `db.DateTime` | 日時型 |
| `default=datetime.utcnow` | 値未指定時のデフォルト。**`utcnow` に `()` を付けていない**点に注意（下記） |

**`default=datetime.utcnow`（カッコ無し）の意味**: `datetime.utcnow()` と**呼ばず**、関数そのものを渡している。
こうすると「行を挿入する**その瞬間**に `utcnow()` が呼ばれて現在時刻が入る」。もし `datetime.utcnow()` と書くと**アプリ起動時刻**が固定で入ってしまう。「関数を渡す」か「呼んだ結果を渡す」かで挙動が変わる典型例。
**既知スタックとの対応**: JS でいう `default: Date.now`（関数参照）と `default: Date.now()`（即時評価）の違いと同じ。

### 🔬 構文解剖: `author_id = db.Column(db.Integer, db.ForeignKey("users.id"), ...)`

| 部品 | 意味 |
|---|---|
| `db.ForeignKey("users.id")` | **外部キー**。この列が `users` テーブルの `id` 列を参照すると宣言 |
| `"users.id"` | `テーブル名.列名`。`__tablename__` で付けた `"users"` を指す |

**外部キーの意味**: 「この記事は、どのユーザーが書いたか」を `author_id` に相手の `id` を入れて表す（＝リレーション）。
**既知スタックとの対応**: Prisma の `authorId Int` + `@relation(fields:[authorId], references:[id])`。RDB の1対多を表す標準手法。

### 🔬 構文解剖: `posts = db.relationship("Post", back_populates="author")`

| 部品 | 意味 |
|---|---|
| `db.relationship(...)` | **DBの列ではなく**、Python 側で関連オブジェクトを辿るための「ナビゲーション」定義 |
| `"Post"` | 関連する相手のモデル名（文字列で指定。まだ定義前でも文字列なら参照できる） |
| `back_populates="author"` | 反対側(`Post.author`)と**双方向で対応付ける**。片方を変えると他方も整合する |

**`relationship` と `ForeignKey` の違い**: `ForeignKey` は**DBに実在する列**（`author_id`）。`relationship` は**Python から `user.posts` や `post.author` と辿るための糖衣**でDBの列ではない。
**既知スタックとの対応**: Prisma の `posts Post[]` / `author User @relation(...)` の、オブジェクトを辿る側に相当。
**使い方の例**: `post.author.username`（記事から著者名）や `user.posts`（ユーザーの記事一覧）と、SQLを書かずにオブジェクトで辿れる。

> 🧠 **この言語（SQLAlchemy）の考え方**: 「テーブル＝クラス、行＝インスタンス、列＝クラス属性」。
> DBの世界を Python のオブジェクトに写像(mapping)するのが ORM。SQL を文字列で書く代わりに、Python の型と関係で表現する。

---

## 2-4. `create_app` に DB を登録する（Step 1 の続き・差分）

`__init__.py` を編集します。**Step 1 のコードに以下を足す差分**です（どこに足すか明示）。

**ファイル: `flaskr-api/flaskr/__init__.py`（Step 1 からの差分を反映した全文）**

```python
from flask import Flask

from .models import db  # ★追加：models.py の db を取り込む


def create_app():
    """Flask アプリを組み立てて返すファクトリ関数。"""
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "dev"
    # ★追加：DB接続先（Docker の MySQL）。Step 0 の docker-compose.yml の値と一致させる
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr"
    )

    db.init_app(app)  # ★追加：db をこのアプリに結び付ける

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
```

### 🔬 構文解剖: `from .models import db`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `.models` | ドットモデルズ | 先頭の `.` は「**同じパッケージ内の**」を表す**相対インポート**。`flaskr/models.py` を指す |
| `import db` | — | `models.py` で作った `db` インスタンスを取り込む |

**先頭 `.` の意味**: `from .models` は「今いる `flaskr` パッケージの中の `models`」。`from models` だと外部トップレベルを探して失敗しうる。**同一パッケージ内の参照は `.` を付ける**のが作法。
**既知スタックとの対応**: TS の相対 import `from "./models"` の `./` と同じ発想。

### 🔬 構文解剖: 接続URL `mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr`

`URL = スキーム://ユーザー:パスワード@ホスト:ポート/DB名` の形。

| 部品 | 値 | 意味 | どこから来た値か |
|---|---|---|---|
| スキーム | `mysql+pymysql` | 「MySQL に pymysql ドライバで繋ぐ」 | 使うDBとドライバ |
| ユーザー | `flaskr` | 接続ユーザー | `docker-compose.yml` の `MYSQL_USER` |
| パスワード | `flaskr` | パスワード | `MYSQL_PASSWORD` |
| ホスト | `127.0.0.1` | 自分のPC。Docker が 3306 をPCに公開している | `ports: "3306:3306"` の左側 |
| ポート | `3306` | MySQL のポート | 同上 |
| DB名 | `flaskr` | 使うデータベース | `MYSQL_DATABASE` |

**なぜ `127.0.0.1` か（`db` ではなく）**: Flask は**コンテナの外（PC上）**で動くので、Docker が公開した `127.0.0.1:3306` に繋ぐ。
`docker-compose.yml` 内のサービス名 `db` で繋げるのは「コンテナ同士」の場合だけ。ここは混同しやすい要注意点。
**既知スタックとの対応**: `DATABASE_URL` 接続文字列。Prisma/Rails 等と同じ「1本のURLに接続情報を詰める」方式。

### 🔬 構文解剖: `db.init_app(app)`

| 部品 | 意味 |
|---|---|
| `db.init_app(app)` | グローバルに作った `db` を、**この `app` に結び付ける**（設定URLを読ませて使える状態にする） |

**なぜ `SQLAlchemy(app)` と一発で書かないか**: `db` は `models.py` で先に作る必要がある（モデルが `db.Model` を使うため）。
そこで「先に空の `db` を作る → アプリができたら `init_app` で結ぶ」の2段構えにする。これがファクトリ＋拡張の定番の型。
**既知スタックとの対応**: 「クライアントを生成 → 設定を注入して初期化」の分離。DI（依存性注入）に近い発想。

### 🔬 構文解剖: 丸カッコで囲んだ複数行の代入

```python
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr"
)
```

| 部品 | 意味 |
|---|---|
| `= (` … `)` | 値を**丸カッコで囲むと複数行に折り返せる**。長い文字列や式を読みやすく分割するため |

**なぜ囲むか**: Python は原則1文1行。丸カッコの中だけは改行できる規則を使い、長いURLを見やすく折っている。機能的な意味はなく整形目的。

---

## 2-5. テーブルを作る（穴埋め・中盤フェード）

DB拡張は登録できましたが、まだ**テーブルは1つもありません**。モデル定義から実テーブルを作る「初期化コマンド」を用意します。

Flask には自作コマンドを `flask xxx` として生やす仕組みがあります。これを使って `flask init-db` を作ります。

**ファイル: `flaskr-api/flaskr/__init__.py` に追記する `create_app` 内の一部**

次の `# TODO` を埋めてください（ヒントは各行に日本語で書いてあります）。

```python
    import click  # ファイル先頭の import 群に移動してもよい

    @app.cli.command("init-db")
    def init_db():
        """モデル定義から全テーブルを作成する。"""
        # TODO(1): アプリ文脈(app context)の中で DB 操作をするため with 文を開く
        #          ヒント: with app.app_context():
        # TODO(2): db が知っている全モデルからテーブルを一括作成する
        #          ヒント: db.create_all()
        # TODO(3): 完了メッセージを表示する
        #          ヒント: click.echo("初期化しました")
```

<details><summary>解答例</summary>

```python
    import click

    @app.cli.command("init-db")
    def init_db():
        """モデル定義から全テーブルを作成する。"""
        with app.app_context():
            db.create_all()
        click.echo("初期化しました")
```

</details>

### 🔬 構文解剖: 埋めた3行

| 部品 | 読み方 | 意味 |
|---|---|---|
| `@app.cli.command("init-db")` | — | デコレータ。`flask init-db` というCLIコマンドを生やす。ハイフン名は慣習 |
| `with app.app_context():` | ウィズ | **with 文**。ブロックの間だけ「アプリ文脈」を有効にし、抜けると自動で後始末する |
| `db.create_all()` | — | `db.Model` を継承した**全モデル**を走査し、まだ無いテーブルをCREATEする |
| `click.echo(...)` | クリック | Flask が内部で使う CLI ライブラリ `click` の出力関数。`print` のCLI版 |

**`with` 文とは**: `with 開く処理 as 変数:` の形で、ブロックを抜けるときに**自動でクリーンアップ**する構文。
ファイルを開いて自動で閉じる、DB接続を借りて自動で返す、といった「開いたら必ず閉じる」処理を安全に書ける。
**なぜ `app_context()` が要るか**: `db` は「今どのアプリに対して操作するか」を知る必要がある。ファクトリ方式では `db` とアプリが別々なので、`app_context()` で「このアプリに対して」と明示する。CLIコマンドやスクリプトからDB操作するときの定番。
**既知スタックとの対応**: `with` は JS の `try/finally` で後始末する定型を、言語構文にしたもの（`using` 宣言に近い）。

> 🏢 **実務メモ**: 実務では `db.create_all()` は**初学者向け・プロトタイプ用**。テーブルを一気に作るだけで、
> 「後から列を1つ足す」等のスキーマ変更を安全に追跡できない。現場では **Alembic / Flask-Migrate** でマイグレーション管理する。
> この教材はまず `create_all()` で全体像を掴み、発展課題でマイグレーションに触れる。

### ⚠️ やりがち
> **やりがち**: `db.create_all()` を「モデルを import する前」に呼び、テーブルが1つも作られない。
> **現場では**: `create_all()` は「その時点で `db` が知っているモデル」だけを作る。`models.py` の `db` を `__init__` が import している構成なら、`create_app` 経由で確実にモデルが読み込まれた状態になる。

---

## 2-6. 🔮 予測 → 動作確認

### 前提: MySQL が起動しているか

```bash
docker compose ps          # db が healthy か確認。していなければ:
docker compose up -d
```

### 🔮 実行前に予想しよう

1. `flask init-db` を実行した後、MySQL には**いくつのテーブル**ができている？その名前は？
2. `users` テーブルには何本の列がある？（モデルを見て数えてみる）

### テーブルを作成

```bash
uv run flask --app flaskr init-db
```

**期待される出力:**

```
初期化しました
```

### 本当にできたか MySQL 側で確認

```bash
docker compose exec db mysql -u flaskr -pflaskr flaskr -e "SHOW TABLES;"
```

**期待される出力:**

```
+------------------+
| Tables_in_flaskr |
+------------------+
| posts            |
| users            |
+------------------+
```

（予想1の答え: `users` と `posts` の**2つ**）

列も確認してみましょう:

```bash
docker compose exec db mysql -u flaskr -pflaskr flaskr -e "DESCRIBE users;"
```

`id` / `username` / `password_hash` の**3列**が出れば成功（予想2の答え）。

---

## 2-7. ✅ 想起チェック

<details><summary>Q1. モデルクラスが `db.Model` を継承すると何が起きる？</summary>

そのクラスが「1つのDBテーブルを表すモデル」になり、SQLAlchemy がクラス属性(`db.Column`)を列に対応付ける（ORM マッピング）。
</details>

<details><summary>Q2. `default=datetime.utcnow` を `default=datetime.utcnow()` と書くと何が変わる？</summary>

`()` 付きは**アプリ起動時に1回だけ評価**され、全行に同じ固定時刻が入ってしまう。`()` 無しは関数参照を渡すので、**行を挿入するたびに呼ばれて**その時刻が入る。
</details>

<details><summary>Q3. 接続URLのホストを `db` ではなく `127.0.0.1` にするのはなぜ？</summary>

Flask はコンテナの外（PC上）で動くから。`ports: "3306:3306"` でPCに公開された `127.0.0.1:3306` に繋ぐ。サービス名 `db` で繋げるのはコンテナ同士の通信のときだけ。
</details>

<details><summary>Q4. `with app.app_context():` は何のために要る？</summary>

ファクトリ方式では `db` とアプリが分離しているため、DB操作時に「どのアプリに対してか」を明示する必要がある。`app_context()` でそれを与え、ブロックを抜けると自動で後始末する。
</details>

---

## ✍️ ブランクページ（章末の再現練習）

ファイルを閉じて、**白紙から** `models.py` を再現してください。
思い出せなかった行に印を付け、その行の `🔬 構文解剖`（2-3）だけ読み返します。

合格ライン:

- `db = SQLAlchemy()` をアプリの外で作っている
- `User` / `Post` が `db.Model` を継承している
- 各モデルに `__tablename__` と主キー `id` がある
- `Post` に `author_id`（`ForeignKey("users.id")`）がある
- 双方向の `db.relationship(... back_populates=...)` がある

さらに、`create_app` に DB を組み込む3点（`SQLALCHEMY_DATABASE_URI` の設定／`db.init_app(app)`／`init-db` コマンド）を、見ないで書けるか試します。

---

## まとめ

- ORM は「**テーブル＝クラス / 行＝インスタンス / 列＝クラス属性**」で DB を Python で表す
- `db = SQLAlchemy()` をアプリの外で作り、`db.init_app(app)` で後から結ぶ（ファクトリの型）
- 接続は `mysql+pymysql://user:pass@127.0.0.1:3306/db` の1本のURL
- `flask init-db` → `db.create_all()` でモデルからテーブルを作成（実務では後にマイグレーションへ）

---

## ここまでのレビュー依頼ポイント

Step 0〜2 を通して、次を確認してください（あなたのレビュー用）:

- 「おまじない」なしで、記号・キーワードまで説明が届いているか
- 🔬 構文解剖の粒度（細かすぎ/粗すぎ）はちょうどよいか
- Docker / uv / Zed デバッグの説明量は、初めてでも進める分量か
- フェード（Step2 の穴埋め）の難易度は適切か

次は **Step 3（認証API：register/login/logout + セッションCookie + Blueprint 導入）** に進みます。
