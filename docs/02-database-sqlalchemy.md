# Step 2: SQLAlchemy でモデルと DB 初期化

← [Step 1](./01-application-factory.md) ／ [目次](./README.md) ／ 次: [Step 3](./03-auth-api.md)

## 🎯 目的

DB のテーブルを **SQLAlchemy のモデルクラス**で定義し、`flask init-db` で DB ファイルを初期化できるようにする。

> **核: モデル定義（`User`/`Post`）と、それを JSON に変換する `to_dict()`。**
> **補足: CLI コマンド化（`init-db`）**。DB 作成は最悪 Python シェルからでもできますが、元記事にならってコマンド化します。

🔁 **置き換え（このステップ全体）**: 元記事は `schema.sql`（生 SQL の `CREATE TABLE`）＋ `db.py`（`sqlite3.connect` / `get_db` / `close_db`）でした。
この教材では **Flask-SQLAlchemy + MySQL** に置き換えます。対応は次のとおり:

| 元記事（sqlite3） | この教材（SQLAlchemy + MySQL） |
|---|---|
| `schema.sql` の `CREATE TABLE user (...)` | `class User(db.Model)` |
| `get_db()` で毎回 `sqlite3.connect` | `db.session`（拡張が接続を管理） |
| `close_db()` を `teardown_appcontext` に登録 | **不要**（Flask-SQLAlchemy が自動でセッションを片付ける） |
| `init_db()` が `schema.sql` を実行 | `db.create_all()` がモデルからテーブル生成 |
| `sqlite3.Row` で dict 風に読む | モデル属性 `post.title` で読む → `to_dict()` で JSON 化 |
| DB ファイル自体を `init_db` が作る | **DB(`flaskr`)は Docker が作成済み**。`init-db` は**テーブル**だけ作る |

> ⚠️ **MySQL 特有の重要ポイント**: MySQL の文字列カラム（`VARCHAR`）は**必ず最大長が必要**です。SQLite は `db.String`（長さ無し）でも動きましたが、MySQL では**長さを指定しないとエラー**になります。そこでこのステップでは `mapped_column(db.String(80))` のように**長さを付けます**（下のコードで明示）。これが SQLite → MySQL で一番ハマりやすい差分です。

前半（`User`）は写経、後半（`Post`）は一部 `# TODO` を自分で埋めます。

---

## 💻 コード

### 2-1. モデル定義

`flaskr/models.py` を新規作成:

```python
from __future__ import annotations

from datetime import UTC, datetime

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 全モデルの共通の親。DeclarativeBase を直接継承すると、型チェッカーが
# コンストラクタ（User(username=...) 等）まで型を効かせられる
class Base(DeclarativeBase):
    pass


# 拡張オブジェクト。model_class に Base を渡して結び付ける
db = SQLAlchemy(model_class=Base)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ユーザー名は一意・必須（MySQL なので長さ必須。80文字まで）。Mapped[str] = NOT NULL
    username: Mapped[str] = mapped_column(db.String(80), unique=True)
    # ハッシュ化したパスワードを保存（ハッシュは長いので255文字。平文は絶対入れない）
    password: Mapped[str] = mapped_column(db.String(255))

    # 1ユーザーが複数 Post を持つ（1対多）
    posts: Mapped[list[Post]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = ...  # TODO(1): user.id を参照する外部キー
    # 作成日時。デフォルトで現在時刻（UTC）を入れる
    created: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    # タイトルも長さ必須（255文字）。本文は長文なので Text 型（長さ指定不要）
    title: Mapped[str] = mapped_column(db.String(255))
    body: Mapped[str] = mapped_column(db.Text, default="")

    # Post 側から著者(User)を辿れるようにする
    author: Mapped[User] = relationship(back_populates="posts")

    def to_dict(self) -> dict:
        """JSON レスポンス用の dict に変換する（Jinja テンプレートの代わり）。"""
        # TODO(2): id / title / body / created(ISO文字列) / author_id / username を返す
        return ...
```

> 💡補足: SQLAlchemy 2.0 のタイプ付き記法（`Mapped[]` / `mapped_column`）を使うと `post.title` が `str` と型で分かり、**mypy**（型チェッカー）の恩恵（補完・型エラー検出・安全なリファクタ）が受けられます。`Mapped[int]` は NOT NULL、`Mapped[X | None]` なら NULL 可、という対応です。モデルは `db.Model` ではなく **`Base`（`DeclarativeBase`）を直接継承**します——これが SQLAlchemy 2.0 の推奨スタイルで、型チェッカーがモデルを正確に解釈できます。

<details><summary>解答例（TODO(1) と TODO(2)）</summary>

```python
    # TODO(1)
    author_id: Mapped[int] = mapped_column(db.ForeignKey("user.id"))

    # TODO(2)
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "created": self.created.isoformat(),
            "author_id": self.author_id,
            "username": self.author.username,  # リレーション経由で著者名を取得
        }
```
</details>

### 2-2. DB 初期化コマンドと登録用ヘルパー

同じ `flaskr/models.py` の末尾に追記:

```python
@click.command("init-db")
def init_db_command() -> None:
    """既存データを消して、モデルからテーブルを作り直す。"""
    db.drop_all()
    db.create_all()
    click.echo("Initialized the database.")


def init_app(app: Flask) -> None:
    # 拡張をこのアプリに結び付ける
    db.init_app(app)
    # `flask init-db` を使えるように登録
    app.cli.add_command(init_db_command)
```

### 2-3. ファクトリから呼び出す

`flaskr/__init__.py` の `return app` の**直前**に追記:

```python
    # ▼ 追記（return app の直前）
    from . import models
    models.init_app(app)

    return app
```

---

## 🧠 解説

**モデルクラス = テーブル定義**
```python
class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(80), unique=True)
```
元記事の `CREATE TABLE user (id INTEGER PRIMARY KEY ..., username TEXT UNIQUE NOT NULL, ...)` と**一対一で対応**します。
`mapped_column` が旧来の `db.Column` を置き換えます。`unique=True` = `UNIQUE`、そして `Mapped[str]`（非 Optional）= `NOT NULL`（`Mapped[str | None]` なら NULL 可）。SQL を Python クラスで書いている、と捉えてください。

> 🔗 **Django との接続**: `mapped_column(...)` は Django の `models.CharField(...)` に相当。`relationship` は Django の `ForeignKey` の逆参照（`related_name`）に近い。「モデル＝テーブル」の発想はそのままです。

**リレーション**
```python
posts: Mapped[list[Post]] = relationship(back_populates="author")   # User 側
author: Mapped[User] = relationship(back_populates="posts")          # Post 側
```
元記事は一覧取得で毎回 `JOIN user u ON p.author_id = u.id` を手書きしていました。
SQLAlchemy では `post.author.username` と**属性アクセスするだけ**で著者名が取れます（`to_dict()` で使用）。JOIN は ORM が裏でやってくれます。

**`to_dict()` が「テンプレートの代わり」**
元記事は `render_template('blog/index.html', posts=posts)` で HTML を組み立てていました。
REST API では HTML を返さず、`to_dict()` で**辞書 → JSON** にして返します。`created.isoformat()` は日時を `"2018-01-01T00:00:00+00:00"` の形式の文字列にして、フロント（React）でパースしやすくするためです。

**`close_db` が消えた理由**
元記事は接続を自前で開き、`teardown_appcontext(close_db)` で閉じていました。
Flask-SQLAlchemy は `db.session` の後片付け（リクエスト終了時のクローズ）を**自動で登録**するため、`close_db` 相当は不要です。これが ORM 拡張を使う利点の一つ。

---

## 🔮 予測 → 動作確認

**実行前に予想してみよう。**
- `flask init-db` は何を作る？（DB そのもの？ テーブル？）
- MySQL コンテナが `healthy` になる前に実行したらどうなる？

まず MySQL が起動して受付可能か確認:
```bash
docker compose ps           # STATUS が "healthy" であること
```

実行:
```bash
uv run flask --app flaskr init-db
```
期待される出力:
```
Initialized the database.
```

確認（Docker の MySQL に入ってテーブルを見る）:
```bash
docker compose exec db mysql -uflaskr -pflaskr flaskr -e "SHOW TABLES;"
```
期待される出力（`user` と `post` の2テーブル）:
```
+------------------+
| Tables_in_flaskr |
+------------------+
| post             |
| user             |
+------------------+
```

> ⚠️ もし `Can't connect to MySQL server` や `Connection refused` が出たら、MySQL がまだ `starting` の可能性大。`docker compose ps` で `healthy` を待ってから再実行してください（[つまずき](./06-frontend-and-wrapup.md#6-3-つまずきポイントよくあるエラーと対処)参照）。
> 💡補足: `flask init-db` が作るのは**テーブル**（`user`/`post`）だけです。**DB `flaskr` 自体は Docker（compose の `MYSQL_DATABASE`）が起動時に作成済み**、という分担を押さえましょう。

---

## ✅ 想起チェック

**見ないで説明してみよう:** 元記事の `schema.sql` と `close_db()` は、この教材ではそれぞれどうなった？ なぜ `close_db` は不要になった？

<details><summary>解答例</summary>

- `schema.sql`（`CREATE TABLE`）→ **モデルクラス**（`class User(db.Model)` / `class Post(db.Model)`）に置き換わり、`db.create_all()` がテーブルを生成する。
- `close_db()` → **不要**。Flask-SQLAlchemy が `db.session` のリクエスト終了時クローズを自動登録するため、手動で `teardown_appcontext` に登録する必要がない。
</details>

**小問:** REST API で、モデルインスタンスをそのまま `jsonify` できない（＝`to_dict()` が要る）のはなぜ？

<details><summary>解答例</summary>

`Post` オブジェクトは Python のクラスインスタンスで、JSON にそのまま変換できないため。`to_dict()` で**シリアライズ可能な辞書**（文字列・数値・ISO 日時文字列など）に整形してから `jsonify` する。これは元記事で Jinja テンプレートが担っていた「データ → 出力形式」の変換に当たる。
</details>

---

次は [Step 3: 認証 API](./03-auth-api.md)。
