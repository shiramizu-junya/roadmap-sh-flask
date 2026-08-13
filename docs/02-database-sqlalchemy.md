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
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 型情報を持つ基底クラス（SQLAlchemy 2.0 スタイル）
class Base(DeclarativeBase):
    pass


# DB拡張のインスタンス。まだアプリには結び付いていない（後で init_app で結ぶ）
db = SQLAlchemy(model_class=Base)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # このユーザーが書いた記事たち（1対多のリレーション）
    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(db.Model):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="posts")
```

> 🧠 **なぜ型つき（SQLAlchemy 2.0 スタイル）にするか**: 列を Python の型注釈（`Mapped[int]` 等）で書くと、
> エディタ（Zed の basedpyright）が `user.username` を補完し、打ち間違いを保存前に赤線で教えてくれる。
> 昔ながらの `db.Column(...)` 方式でも動くが、**型の恩恵（補完・検査）が消える**ので、この教材は 2.0 スタイルに統一する。

---

## 2-3. 🔬 構文解剖

### 🔬 構文解剖: import 群

| 行 | 意味 |
|---|---|
| `from datetime import datetime, timezone` | `datetime` モジュールから `datetime` クラスと `timezone`（タイムゾーン）を取り出す。JS の `Date` に相当 |
| `from flask_sqlalchemy import SQLAlchemy` | Flask 用の SQLAlchemy 統合。`db` を作る |
| `from sqlalchemy import ForeignKey, String, Text` | 列の型（`String`/`Text`）と外部キー（`ForeignKey`）。**型つき方式では `db.String` ではなくこちらを直接 import する** |
| `from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship` | 型つきモデルの4点セット。次で解剖する |

**既知スタックとの対応**: TS で「型と関数を名前付き import する」のと同じ。`from A import B, C` は「A から B と C を取り出す」。

### 🔬 構文解剖: `class Base(DeclarativeBase): pass` と `db = SQLAlchemy(model_class=Base)`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `class Base(DeclarativeBase):` | — | すべてのモデルの**親クラス**を自分で用意する。`DeclarativeBase` を継承すると「型情報を持つ ORM の土台」になる |
| `pass` | パス | **「何もしない」を表すキーワード**。クラス本体が空のときの穴埋め。Python はブロックを空にできないので必ず要る |
| `SQLAlchemy(model_class=Base)` | — | その `Base` を「モデルの基底」に指定して `db` を作る。以降 `db.Model` は `Base` を指す |

**なぜ `Base` を自作するのか**: SQLAlchemy 2.0 の型つき方式（`Mapped`）を使うには、`DeclarativeBase` を継承した基底クラスが要る。`model_class=Base` で Flask-SQLAlchemy にそれを教える。
**`pass` とは**: 「ここは意図的に空」と示す文。中身のないクラスや関数の体裁を保つために置く。JS の空 `{}` に近いが、Python は明示的に `pass` と書く。
**なぜアプリの外で作るか**: `db` をグローバルに1個作り、後で `db.init_app(app)` でアプリに結ぶ。こうすると `models.py`（モデル定義）と `__init__.py`（組み立て）を分離でき、循環インポートを避けられる（Step 1 のファクトリの利点）。
**既知スタックとの対応**: `db` は「シングルトンの拡張インスタンスを後で初期化する」パターン。Prisma Client を1つ作って使い回すのに近い。

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

### 🔬 構文解剖: `id: Mapped[int] = mapped_column(primary_key=True)`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `id` | — | クラス直下に書く**クラス属性**。これ1つが1つの**カラム（列）**になる |
| `: Mapped[int]` | マップト | **型注釈**。「この属性はDB列に対応し、Python では `int` として扱う」。`Mapped[...]` が「ORM列だよ」の印 |
| `= mapped_column(...)` | マップトカラム | 実際の**列定義**。オプション（主キー・長さ・外部キー等）はここに書く |
| `primary_key=True` | — | **キーワード引数**（`名前=値`）。この列を主キーにする |

**`Mapped[int]` の効き目**: 型を書くと2つ効く。①`Integer` 型の列だと SQLAlchemy が**推論**するので `db.Integer` を書かなくてよい。②エディタ（basedpyright）が `user.id` を `int` として補完・検査する。
**キーワード引数とは**: `primary_key=True` のように `名前=値` で渡す引数。位置に依存せず、何を指定しているか読んで分かる。
**既知スタックとの対応**: TS の型付きプロパティ宣言に近い。Prisma の `id Int @id`、TypeORM の `@PrimaryGeneratedColumn()` に相当。
**なぜ主キーを整数の id にするか**: 各行を一意に識別する列が要る。整数の自動採番が最も素直（MySQL では `AUTO_INCREMENT` になる）。

### 🔬 構文解剖: 各カラムの型とオプション（型つき方式の肝）

```python
username: Mapped[str] = mapped_column(String(80), unique=True)
body: Mapped[str] = mapped_column(Text)
```

| 部品 | 意味 |
|---|---|
| `Mapped[str]` | 文字列の列。**非NULL（NOT NULL）を型で表現**するので、`nullable=False` を書かなくてよい |
| `String(80)` | 可変長文字列。最大80文字。MySQL の `VARCHAR(80)`。`str` は長さが要るので**型を明示して渡す** |
| `Text` | 長い文章用の型（`body` で使用）。`String` と違い長さ上限を実質気にしない |
| `unique=True` | この列は**重複禁止**（同じ username を2人持てない） |
| （NULL を許可したいとき） | `Mapped[str \| None]` と書く。`\| None` を付けた列だけ NULL 可になる |

**型つき方式の最重要ルール**: `Mapped[str]`（非Optional）＝**NOT NULL**、`Mapped[str \| None]`＝**NULL可**。
つまり **`nullable` は型で決まる**ので、原則 `nullable=False` は書かない。旧方式（`db.Column(..., nullable=False)`）から来るとここが一番の違い。
**なぜ `int` は型省略でき `str` は `String(80)` が要るのか**: `int`→`Integer` は一意に決まるが、文字列は「最大何文字か」が決まらないと MySQL の列型を作れない。だから `str` は長さ付きで明示する。

### 🔬 構文解剖: `created: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `Mapped[datetime]` | — | 日時型の列 |
| `default=...` | — | 値未指定時のデフォルト |
| `lambda: ...` | ラムダ | **その場で作る名前なしの関数**。JS の `() => ...`（アロー関数）に相当 |
| `datetime.now(timezone.utc)` | — | 現在の UTC 時刻を返す |

**なぜ `lambda:` で包むのか**: `default` に「**呼んだ結果**」ではなく「**関数そのもの**」を渡すため。
`default=datetime.now(timezone.utc)` と書くと**アプリ起動時刻**が固定で全行に入ってしまう。`lambda:` で包むと「行を挿入する**その瞬間**に呼ばれて」その時刻が入る。
**既知スタックとの対応**: JS の `default: () => new Date()`（毎回評価）と `default: new Date()`（1回だけ評価）の違いと同じ。
**💡 補足**: 昔の教材は `default=datetime.utcnow`（関数参照）と書くが、`utcnow` は Python 3.12 以降**非推奨**。この教材はタイムゾーン付きの `datetime.now(timezone.utc)` を `lambda` で渡す形に統一する。

### 🔬 構文解剖: `author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))`

| 部品 | 意味 |
|---|---|
| `ForeignKey("users.id")` | **外部キー**。この列が `users` テーブルの `id` 列を参照すると宣言 |
| `"users.id"` | `テーブル名.列名`。`__tablename__` で付けた `"users"` を指す |

**外部キーの意味**: 「この記事は、どのユーザーが書いたか」を `author_id` に相手の `id` を入れて表す（＝リレーション）。
**既知スタックとの対応**: Prisma の `authorId Int` + `@relation(fields:[authorId], references:[id])`。RDB の1対多を表す標準手法。

### 🔬 構文解剖: `posts: Mapped[list["Post"]] = relationship(back_populates="author")`

| 部品 | 意味 |
|---|---|
| `relationship(...)` | **DBの列ではなく**、Python 側で関連オブジェクトを辿るための「ナビゲーション」定義 |
| `Mapped[list["Post"]]` | **1対多**を型で表す。「`Post` の**リスト**」＝ユーザーは複数記事を持つ。多対1側は `Mapped["User"]`（単数） |
| `"Post"` | 相手のモデル名（文字列指定。まだ定義前でも文字列なら前方参照できる） |
| `back_populates="author"` | 反対側(`Post.author`)と**双方向で対応付ける**。片方を変えると他方も整合する |

**`relationship` と `ForeignKey` の違い**: `ForeignKey` は**DBに実在する列**（`author_id`）。`relationship` は**Python から `user.posts` や `post.author` と辿るための糖衣**でDBの列ではない。
**型で件数まで表す**: `Mapped[list["Post"]]`＝多側（複数）、`Mapped["User"]`＝1側（単数）。型を見ればリレーションの向きが分かる。
**既知スタックとの対応**: Prisma の `posts Post[]` / `author User @relation(...)` に相当。
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

そのクラスが「1つのDBテーブルを表すモデル」になり、SQLAlchemy がクラス属性(`mapped_column(...)`)を列に対応付ける（ORM マッピング）。
</details>

<details><summary>Q2. `default=lambda: datetime.now(timezone.utc)` を `default=datetime.now(timezone.utc)`（lambda なし）と書くと何が変わる？</summary>

`lambda` なしは**アプリ起動時に1回だけ評価**され、全行に同じ固定時刻が入ってしまう。`lambda:` で包むと関数を渡すので、**行を挿入するたびに呼ばれて**その時刻が入る。
</details>

<details><summary>Q2-b. `Mapped[str]` と `Mapped[str | None]` の違いは？</summary>

`Mapped[str]`（非Optional）は **NOT NULL**、`Mapped[str | None]` は **NULL可**。型つき方式では `nullable` を型で表すので、`nullable=False` を個別に書かない。
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

- `class Base(DeclarativeBase)` を作り、`db = SQLAlchemy(model_class=Base)` をアプリの外で作っている
- `User` / `Post` が `db.Model` を継承している
- 各列が `名前: Mapped[型] = mapped_column(...)` の形（`Mapped[str]` は非NULL）
- 各モデルに `__tablename__` と主キー `id` がある
- `Post` に `author_id`（`mapped_column(ForeignKey("users.id"))`）がある
- 双方向の `relationship(... back_populates=...)`（1対多は `Mapped[list["Post"]]`）がある

さらに、`create_app` に DB を組み込む3点（`SQLALCHEMY_DATABASE_URI` の設定／`db.init_app(app)`／`init-db` コマンド）を、見ないで書けるか試します。

---

## まとめ

- ORM は「**テーブル＝クラス / 行＝インスタンス / 列＝クラス属性**」で DB を Python で表す
- 列は **`名前: Mapped[型] = mapped_column(...)`**（SQLAlchemy 2.0 型つき方式）。`Mapped[str]`＝NOT NULL、`Mapped[str | None]`＝NULL可
- `class Base(DeclarativeBase)` + `db = SQLAlchemy(model_class=Base)` をアプリの外で作り、`db.init_app(app)` で後から結ぶ（ファクトリの型）
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
