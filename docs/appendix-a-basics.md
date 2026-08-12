# 付録A: Python / Flask / SQLAlchemy の基礎お作法（`models.py` / `__init__.py` 精読）

← [目次に戻る](./README.md)

Flask も SQLAlchemy も初めて、という前提で、**Python の記法そのものから** 2つの中心ファイルを1行ずつ読み解きます。まず「読むのに必要な Python のお作法」を押さえ、その後にファイルを逐行解説します。

---

## 0. 先に押さえる Python の記法（お作法）

以降のコードで繰り返し出てくる文法です。ここだけ読めば残りが読めます。

### 0-1. import（他ファイルの機能を持ち込む）
```python
import os                              # os モジュール全体 → os.環境変数 のように使う
from flask import Flask               # flask パッケージから Flask だけを名前で持ち込む
from datetime import UTC, datetime    # 複数を一度に持ち込む（カンマ区切り）
from . import models                  # 「.」＝同じパッケージ内。相対 import
```
- `import X` … `X.機能` で使う
- `from X import Y` … `Y` を直接使える
- `from . import Y` … **同じフォルダ（パッケージ）内**の `Y.py` を持ち込む（`.` が「ここ」）

### 0-2. 型ヒント（型注釈）
Python は型を書かなくても動きますが、**書くと mypy などがチェック**してくれ、補完も効きます。
```python
def create_app(test_config: dict | None = None) -> Flask:
#                          ^^^^^^^^^^^^^  ^^^^^^^   ^^^^^^^^
#                          引数の型        既定値    戻り値の型
```
- `変数: 型` … 変数・引数の型を宣言（`x: int`）
- `-> 型` … 関数の戻り値の型（`-> Flask`、返さないなら `-> None`）
- `A | B` … 「A または B」（`dict | None` は「辞書 または None」）
- `list[Post]` … 「Post の**リスト**」。`[]` の中に要素の型を書く（ジェネリック）
- `Mapped[int]` … SQLAlchemy 用の「int を保持するカラム」という型（後述）

### 0-3. クラスと継承
```python
class Base(DeclarativeBase):   # Base という「設計図」。( ) 内の DeclarativeBase を「継承」する
    pass                        # 中身が空のときの置き字（何もしない）
```
- `class 名前(親):` … クラス定義。**親クラスの機能を引き継ぐ**（継承）
- `pass` … 「本体は空です」という文法上の穴埋め
- クラスの中に書いた `名前: 型 = 値` は**クラスの属性**（そのクラス共通の項目）

### 0-4. メソッドと `self`
```python
class Post(Base):
    def to_dict(self) -> dict:   # クラスの中の関数＝メソッド
        return {"id": self.id}    # self ＝「その인스タンス自身」。self.id で自分の値を参照
```
- クラス内の関数（メソッド）は第1引数に必ず **`self`**（自分自身）を取る
- `self.属性` で、そのオブジェクトの値にアクセスする

### 0-5. デコレータ（`@`）
関数の**上**に付ける `@名前` は、その関数を「包んで機能を足す」印です。
```python
@app.route("/hello")     # ← デコレータ。「この関数を URL /hello に結びつけて」
def hello() -> str:
    return "Hello, World!"
```
`@app.route("/hello")` は「`hello` 関数を `app.route` で登録する」という意味。中身を自分で書かなくても、Flask や Click が裏で処理してくれます。

### 0-6. その他の小物
- `lambda: 式` … 名前のない小さな関数（`lambda: datetime.now(UTC)` は「呼ばれたら今の時刻を返す関数」）
- `is not None` … 「None ではない」の判定（`==` でなく `is` で None を比較するのが作法）
- `__name__`, `__tablename__` … 前後が `__`（ダンダー）の名前は**特別な意味を持つ予約的な名前**
- `"""..."""` … 関数直下の三連引用符は **docstring**（その関数の説明。実行に影響しない）

---

## 1. `flaskr/__init__.py` — アプリケーションファクトリ

```python
import os

from flask import Flask


def create_app(test_config: dict | None = None) -> Flask:
    # アプリ本体を生成・設定する「ファクトリ関数」
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    if app.debug:
        from . import sql_debug

        sql_debug.enable()

    @app.route("/hello")
    def hello() -> str:
        return "Hello, World!"

    from . import models

    models.init_app(app)
    return app
```

### 逐行解説

**`__init__.py` というファイル名の意味**
`__init__.py` があるフォルダは「**パッケージ**（import できるコードのまとまり）」になります。ここでは中に `create_app` を置き、「`flaskr` パッケージ＝アプリを作る場所」にしています。

**`app = Flask(__name__, instance_relative_config=True)`**
- `Flask(...)` … Flask 本体を1つ作る（この `app` が全ての中心）
- `__name__` … 「今このファイルの名前」を自動で入れる特別変数。Flask が**ファイルの場所を知って**テンプレートや設定のパスを解決するのに使う。**お決まりの書き方**として覚えてOK
- `instance_relative_config=True` … 設定ファイルを `instance/` フォルダ基準にする、という指定

**`app.config.from_mapping(...)`**
`app.config` はアプリの設定を入れる辞書のようなもの。`from_mapping(キー=値, ...)` でまとめて設定します。
```python
SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
```
- `キー=値` … これは関数呼び出しの**キーワード引数**（「この名前の引数にこの値」）
- `os.environ.get("SECRET_KEY", "dev")` … OSの環境変数 `SECRET_KEY` を読み、**無ければ第2引数の `"dev"`** を使う（`.env` から読み込まれる）
- `SQLALCHEMY_DATABASE_URI` … DBの接続先。`os.environ.get("DATABASE_URL")` は無ければ `None`

**`if test_config is not None:`**
- `if 条件:` … 条件が真ならインデント（字下げ）した中を実行。**Python はインデントでブロックを表す**（`{}` は使わない）
- テスト時だけ渡される設定で上書きする分岐

**`os.makedirs(app.instance_path, exist_ok=True)`**
- `instance/` フォルダを作る。`exist_ok=True` は「もう有っても эラーにしない」

**`if app.debug:` と入れ子の import**
```python
if app.debug:
    from . import sql_debug
    sql_debug.enable()
```
- `app.debug` … `--debug` で起動したとき `True`
- 関数の**途中で import** している（遅延 import）。デバッグ時だけ必要なので、そのときだけ読み込む書き方

**`@app.route("/hello")` + `def hello()`**
```python
@app.route("/hello")
def hello() -> str:
    return "Hello, World!"
```
- デコレータ `@app.route("/hello")` が「**URL `/hello` に来たら `hello` を呼ぶ**」と登録
- `def hello() -> str:` … 引数なし・文字列を返す関数
- `return "..."` … これがブラウザへの応答になる

**`from . import models` / `models.init_app(app)` / `return app`**
- 同パッケージの `models.py` を持ち込み、`init_app(app)` で DB をこのアプリに結び付ける
- 最後に完成した `app` を `return`（呼び出し元に返す）

> 🔗 **なぜ関数にする？** これが「アプリケーションファクトリ」。詳しくは [Step 1](./01-application-factory.md)。

---

## 2. `flaskr/models.py` — モデル（テーブル定義）

```python
from __future__ import annotations

from datetime import UTC, datetime

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(80), unique=True)
    password: Mapped[str] = mapped_column(db.String(255))

    posts: Mapped[list[Post]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(db.ForeignKey("user.id"))
    created: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    title: Mapped[str] = mapped_column(db.String(255))
    body: Mapped[str] = mapped_column(db.Text, default="")

    author: Mapped[User] = relationship(back_populates="posts")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "created": self.created.isoformat(),
            "author_id": self.author_id,
            "username": self.author.username,
        }


@click.command("init-db")
def init_db_command() -> None:
    db.drop_all()
    db.create_all()
    click.echo("Initialized the database.")


def init_app(app: Flask) -> None:
    db.init_app(app)
    app.cli.add_command(init_db_command)
```

### 逐行解説

**`from __future__ import annotations`**
おまじない的な1行ですが意味があります。これを書くと**型注釈が「後で評価」される**ようになり、**まだ定義していないクラスを型に書ける**ようになります。例えば `User` の中で `list[Post]` と書きたいが `Post` は下で定義される——この行があると引用符 `"Post"` 無しで書けます。

**`from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship`**
SQLAlchemy でモデルを書くための4点セットを持ち込みます（それぞれ後述）。

**`class Base(DeclarativeBase): pass`**
全モデルの**共通の親**。SQLAlchemy の `DeclarativeBase` を継承した空クラスを1つ用意し、以降のモデルはこれを継承します。「テーブルの土台」と思ってください。

**`db = SQLAlchemy(model_class=Base)`**
Flask-SQLAlchemy の拡張オブジェクト。`model_class=Base` で「この Base を土台に使う」と結び付けます。`db.session`（DB操作）や `db.String` などがここから生えます。

**`class User(Base):` … クラス＝テーブル**
```python
class User(Base):
    __tablename__ = "user"
```
- `class User(Base):` … `User` テーブルを表すクラス。`Base` を継承
- `__tablename__ = "user"` … 実際のテーブル名。`__tablename__` は SQLAlchemy が見る**特別な属性名**

**`id: Mapped[int] = mapped_column(primary_key=True)` ← 最重要の型**
1カラムをこの1行で定義します。左右で役割が違います:
- `id: Mapped[int]` … **Python から見た型**。「`user.id` は `int`」。`Mapped[T]` が「T を保持するDBカラム」という印
- `= mapped_column(primary_key=True)` … **DB側の設定**。`primary_key=True` は主キー
- つまり「**型（左）＋ DB設定（右）**」をセットで書くのがお作法

他のカラムも同じ形:
```python
username: Mapped[str] = mapped_column(db.String(80), unique=True)
#         型は str      DBは VARCHAR(80)・一意制約(unique)
password: Mapped[str] = mapped_column(db.String(255))
```
- `db.String(80)` … 文字列カラム（MySQLは最大長必須なので `80`）。`db.Text` は長文用、`db.ForeignKey("user.id")` は外部キー
- **NULL可否は型で表す**: `Mapped[str]`（非Optional）＝ **NOT NULL**、`Mapped[str | None]` ＝ NULL可

**リレーション（テーブル同士の関連）**
```python
# User 側
posts: Mapped[list[Post]] = relationship(back_populates="author")
# Post 側
author: Mapped[User] = relationship(back_populates="posts")
```
- `relationship(...)` … テーブル間の関連を張る。カラムではなく「**辿るための道**」
- `Mapped[list[Post]]` … User から見て「Post の**複数**」（1対多の“多”側）
- `Mapped[User]` … Post から見て「著者は User **1人**」
- `back_populates="..."` … 双方向の対応付け。「User.posts と Post.author はペア」と互いに指定
- これにより `post.author.username`（著者名）を**属性アクセスだけで**取れる（裏で JOIN してくれる）

**`created: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))`**
- `default=...` … 値を入れなかったときの初期値
- `lambda: datetime.now(UTC)` … **「呼ばれた瞬間の UTC 時刻を返す関数」**。`datetime.now(UTC)` を直接書くと“定義時の一瞬”で固定されてしまうので、**関数(lambda)にして「挿入のたびに実行」**させる、という作法

**`def to_dict(self) -> dict:` … メソッド**
```python
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "created": self.created.isoformat(),
        "username": self.author.username,
    }
```
- `self` … このオブジェクト自身。`self.id` で自分の id
- `{ "キー": 値, ... }` … Python の**辞書**（JSON の元）
- `self.created.isoformat()` … 日時オブジェクトを `"2026-01-01T00:00:00+00:00"` の**文字列**に（JSONにできる形へ）
- `self.author.username` … リレーションを辿って著者名を取得
- REST API で JSON を返すための「オブジェクト → 辞書」変換。詳しくは [Step 2](./02-database-sqlalchemy.md)

**`@click.command("init-db")` + `def init_db_command()`**
```python
@click.command("init-db")
def init_db_command() -> None:
    db.drop_all()
    db.create_all()
    click.echo("Initialized the database.")
```
- デコレータ `@click.command("init-db")` が、この関数を **`flask init-db` というCLIコマンド**にする
- `db.drop_all()` … 全テーブル削除、`db.create_all()` … モデルからテーブル作成
- `click.echo(...)` … `print` のCLI版（ターミナルに表示）

**`def init_app(app: Flask) -> None:`**
```python
def init_app(app: Flask) -> None:
    db.init_app(app)
    app.cli.add_command(init_db_command)
```
- `app: Flask` … 引数 `app` は `Flask` 型、戻り値なし（`-> None`）
- `db.init_app(app)` … 拡張(`db`)を**このアプリに結び付ける**（ファクトリ方式の要）
- `app.cli.add_command(...)` … 上の `init-db` コマンドをアプリに登録

---

## 3. お作法チートシート

| 記法 | 意味 |
|---|---|
| `from . import X` | 同じパッケージ内の `X.py` を持ち込む |
| `x: 型` / `-> 型` | 変数・戻り値の型注釈 |
| `A | None` | A または None |
| `list[Post]` / `Mapped[int]` | 要素/対象の型を `[]` で指定 |
| `class C(親):` | クラス定義＋継承 |
| `pass` | 空ブロックの穴埋め |
| `def m(self):` | メソッド（`self`＝自分自身） |
| `@deco` | デコレータ（関数を包んで機能追加） |
| `lambda: 式` | 名前なしの小さな関数 |
| `__name__` / `__tablename__` | 特別な意味を持つダンダー名 |
| `is not None` | None でない判定 |
| `id: Mapped[int] = mapped_column(...)` | SQLAlchemy: 型(左)＋DB設定(右)で1カラム |
| `relationship(back_populates=...)` | テーブル間の関連（属性で辿れる） |

---

## ✅ 想起チェック

**見ないで説明してみよう:** `id: Mapped[int] = mapped_column(primary_key=True)` の「左辺」と「右辺」はそれぞれ何を決めている？

<details><summary>解答例</summary>

- **左辺 `id: Mapped[int]`** … Python から見たときの型（`user.id` は `int`）。`Mapped[T]` は「T を保持するDBカラムだ」という印で、mypy 等の型チェック・補完が効く。
- **右辺 `mapped_column(primary_key=True)`** … データベース側の設定（ここでは主キー）。長さ・一意制約・外部キー・デフォルト値などもここに書く。
「型（左）＋ DB設定（右）」をセットで書く、が SQLAlchemy 2.0 のお作法。
</details>

---

← [目次に戻る](./README.md) ／ 本編は [Step 1](./01-application-factory.md) から
