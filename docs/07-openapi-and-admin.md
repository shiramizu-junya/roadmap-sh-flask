# Step 7: 発展編 — OpenAPI/Swagger UI（APIFlask）& 管理画面（Flask-Admin）

← [Step 6](./06-frontend-and-wrapup.md) ／ [目次](./README.md)

## 概要

完成した `flaskr-api`（[Step 1〜5](./01-application-factory.md)）に、実務でよく足す2つを載せます。**独立した2テーマ**なので、片方だけでもOKです。

1. **OpenAPI + Swagger UI**（**APIFlask**）… API 仕様を自動生成し、`/docs` でブラウザから試せるようにする
2. **管理画面**（**Flask-Admin**）… SQLAlchemy モデルから CRUD 管理画面を `/admin` に自動生成する

> **前提**: [Step 1〜5](./01-application-factory.md) の `flaskr` が動いていること（`User`/`Post` モデル、`auth`/`blog` Blueprint、セッション認証）。
> **これは発展（任意）。** 基礎（手動バリデーション・`to_dict`）を先に理解した上で、それを**自動化する道具**に置き換える、という順序です。

---

# Part A: OpenAPI + Swagger UI（APIFlask）

## 🎯 目的

`Flask` を **`APIFlask`** に置き換え、スキーマで入出力を定義して、**OpenAPI 仕様（`/openapi.json`）と Swagger UI（`/docs`）を自動生成**する。手書きの `to_dict()` と `if not title:` はスキーマに置き換わる。

> **核: スキーマ（`@bp.input`/`@bp.output`）で「検証・整形・ドキュメント」を1つにまとめる**こと。
> **補足: エラー形式のカスタマイズ**（既存の `{"error":...}` を保つ）。

🔁 **置き換え**: `Flask`→`APIFlask`、`Blueprint`→`APIBlueprint`、手動検証→`@bp.input(スキーマ)`、`to_dict()`+`jsonify`→`@bp.output(スキーマ)`。

## A-1. 依存を追加

```bash
uv add apiflask
```
`apiflask` は Flask のサブクラスで、marshmallow・webargs・apispec を内包します（Flask は入ったまま）。

## A-2. スキーマを定義

`flaskr/schemas.py` を新規作成:

```python
from apiflask import Schema
from apiflask.fields import Integer, String, DateTime, Function
from apiflask.validators import Length


class PostIn(Schema):
    """リクエスト検証用（POST/PUT の body）。"""
    title = String(required=True, validate=Length(1, 255))
    body = String(load_default="")            # 省略時は空文字


class PostOut(Schema):
    """レスポンス整形＋ドキュメント用。"""
    id = Integer()
    title = String()
    body = String()
    created = DateTime()
    author_id = Integer()
    # username は Post 直下に無く author 経由なので Function で解決
    username = Function(lambda post: post.author.username)
```

## A-3. ファクトリを APIFlask に

`flaskr/__init__.py` を次のように変更:

```python
import os
from typing import Any

from apiflask import APIFlask          # ← Flask から変更
from flask_cors import CORS


def create_app(test_config: dict | None = None) -> APIFlask:
    # ← APIFlask に。title/version は OpenAPI のメタ情報になる
    app = APIFlask(__name__, title="Flaskr API", version="1.0.0",
                   instance_relative_config=True)
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

    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}},
         supports_credentials=True)

    # ▼ 既存の @app.errorhandler(HTTPException) は削除する。
    #   代わりに error_processor で、これまでの {"error": ...} 形式を維持する。
    @app.error_processor
    def handle_error(e: Any):
        # e.message（文言）/ e.detail（検証内訳）/ e.status_code / e.headers
        body = {"error": e.message}
        if e.detail:
            body["detail"] = e.detail        # バリデーション時の詳細
        return body, e.status_code, e.headers

    from . import models
    models.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)
    from . import blog
    app.register_blueprint(blog.bp)

    return app
```

> ⚠️ **重要**: 元の `@app.errorhandler(HTTPException)`（`{"error": e.description}` を返す）は**削除**します。APIFlask は独自にエラーを処理し、`@app.error_processor` でその形式を一括制御します。ここで `{"error": ...}` に揃えることで、[Step 6](./06-frontend-and-wrapup.md) の React 側 `api.ts`（`data?.error` を読む）もそのまま動きます。

## A-4. blog Blueprint を移行

`flaskr/blog.py`:

```python
from apiflask import APIBlueprint, abort     # ← Flask の Blueprint / werkzeug の abort から変更
from flask import g

from .auth import login_required
from .models import db, Post
from .schemas import PostIn, PostOut

bp = APIBlueprint("blog", __name__, url_prefix="/posts")


def get_post(id: int, check_author: bool = True) -> Post:
    post = db.session.get(Post, id)
    if post is None:
        abort(404, message=f"Post id {id} doesn't exist.")   # apiflask.abort は message=
    if check_author and post.author_id != g.user.id:
        abort(403)
    return post


@bp.get("")
@bp.output(PostOut(many=True))          # 一覧なので many=True
def index():
    return db.session.scalars(db.select(Post).order_by(Post.created.desc())).all()   # ORM を返すだけ


@bp.post("")
@login_required                          # ← input/output の「外側」に置くのが肝（後述）
@bp.input(PostIn)
@bp.output(PostOut, status_code=201)
def create(json_data: dict):             # 検証済みデータは json_data で受け取る
    post = Post(title=json_data["title"], body=json_data["body"], author_id=g.user.id)
    db.session.add(post)
    db.session.commit()
    return post


@bp.get("/<int:id>")
@bp.output(PostOut)
def show(id: int):
    return get_post(id, check_author=False)


@bp.put("/<int:id>")
@login_required
@bp.input(PostIn)
@bp.output(PostOut)
def update(id: int, json_data: dict):
    post = get_post(id)
    post.title = json_data["title"]
    post.body = json_data["body"]
    db.session.commit()
    return post


@bp.delete("/<int:id>")
@login_required
@bp.output(PostOut, status_code=204)     # 204 は本文なし
def delete(id: int):
    post = get_post(id)
    db.session.delete(post)
    db.session.commit()
    return ""
```

> `auth.py` も同じ要領で `APIBlueprint` + スキーマ化できます（`RegisterIn`/`LoginIn`/`UserOut` を作る）。まずは blog で仕組みを掴んでから広げるのがおすすめ。`to_dict()` はレスポンス整形に使わなくなるので、他で参照していなければ削除して構いません。

## 🧠 解説

**デコレータの順序が最重要**
```python
@bp.post("")        # ① ルート登録（一番外）
@login_required     # ② 認証ガード（input/output より外）
@bp.input(PostIn)   # ③ body を検証して json_data に
@bp.output(PostOut) # ④ 戻り値を整形
def create(json_data): ...
```
`@login_required` を **`@bp.output` の外側**に置くのが肝です。もし内側に置くと、未ログイン時に返す 401 レスポンスを `@bp.output` が `PostOut` で整形しようとして壊れます。外側なら**認証で弾く 401 が先に返り**、input/output を通りません。

**`@bp.input` / `@bp.output` が置き換えたもの**
- `@bp.input(PostIn)` … `request.get_json()` + `if not title:` を**丸ごと**代替。検証 NG は自動で **422**（`{"error": "Validation error", "detail": {...}}`）
- `@bp.output(PostOut)` … `to_dict()` + `jsonify()` を代替。**ORM オブジェクトを返すだけ**でスキーマが整形

**エラー形式**: APIFlask 標準は `{"message":..., "detail":...}` です。A-3 の `error_processor` で `{"error":...}` に統一しました。`abort()` は `apiflask.abort(404, message="...")` の `message=` でカスタム文言を渡せます（werkzeug の `abort` だと文言が消えるので注意）。

## 🔮 予測 → 動作確認

**実行前に予想してみよう:** `/docs` を開くと何が見える？ `title` を空で POST したらステータスは？

```bash
uv run flask --app flaskr run --debug
```
- ブラウザで **`http://localhost:5000/docs`** → **Swagger UI**（各エンドポイントを画面から試せる）
- **`http://localhost:5000/openapi.json`** → OpenAPI 3 仕様（JSON）

```bash
# 検証エラー → 422 を予想
curl -s -X POST http://127.0.0.1:5000/posts \
  -H "Content-Type: application/json" -d '{"title":"","body":"x"}'
```
期待される出力（`error_processor` で整形済み）:
```json
{"error":"Validation error","detail":{"json":{"title":["Length must be between 1 and 255."]}}}
```

- 未ログインで作成 → **401** `{"error":"Login required."}`（`login_required` が先に効く）
- 存在しない記事 → **404** `{"error":"Post id 999 doesn't exist."}`（`apiflask.abort` の message）

## つまずきポイント（Part A）

| 症状 | 原因・対処 |
|---|---|
| 未ログイン時に 500 / 変なエラー | `@login_required` が `@bp.output` の**内側**にある。**外側**（ルート直下）へ |
| エラーが `{"message":...}` で返る | `error_processor` 未設定。A-3 の `@app.error_processor` を入れる |
| 404 の文言が "Not Found" になる | `werkzeug` の `abort` を使っている。`from apiflask import abort` にして `message=` |
| `username` が出ない/エラー | `PostOut` の `username` を `Function(lambda p: p.author.username)` にする |
| `json_data` が渡ってこない | `@bp.input` を付け忘れ。付ければ view 引数に `json_data` が入る |

## ✅ 想起チェック（Part A）

**見ないで説明してみよう:** `@bp.input` と `@bp.output` は、Step3/4 で手書きしていた何を置き換えた？

<details><summary>解答例</summary>

- `@bp.input(PostIn)` … `request.get_json()` による取得と、`if not title:` などの**手動バリデーション**（NG は自動で 422）。
- `@bp.output(PostOut)` … `to_dict()` による辞書化と `jsonify()` による**レスポンス整形**（ORM を返すだけでよくなる）。
副産物として、これらの定義から **OpenAPI 仕様と Swagger UI が自動生成**される。
</details>

## 🎁 おまけ: React 側で型付きクライアント自動生成

`/openapi.json` があれば、フロントの API 型を手書きしなくて済みます:
```bash
# frontend/ で
npx openapi-typescript http://localhost:5000/openapi.json -o src/api-types.ts
```
[Step 6](./06-frontend-and-wrapup.md) の手書き `api.ts` の型を、これで**自動生成・自動追従**にできます（バック↔フロントの型ズレが消える）。

---

# Part B: 管理画面（Flask-Admin）

## 🎯 目的

**Flask-Admin** で、`User`/`Post` を管理する CRUD 画面を **`/admin`** に自動生成する。**管理者だけ**アクセスできるようにガードする。

> **核: `is_accessible()` による認可**（無認証で晒さない）。CRUD 画面自体はモデルを登録するだけで出る。
> **補足: サーバレンダリングの管理画面は React SPA とは別系統**（内部管理用途なのでそれで良い）。

## B-1. 依存とモデル変更

```bash
uv add flask-admin
```

`flaskr/models.py` の `User` に **管理者フラグ**を追加:
```python
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column()
    is_admin: Mapped[bool] = mapped_column(default=False)   # ← 追加
    posts: Mapped[list[Post]] = relationship(back_populates="author")
```
列を足したので DB を作り直します:
```bash
uv run flask --app flaskr init-db
```

## B-2. 管理画面（認可付き）

`flaskr/admin.py` を新規作成:

```python
from typing import Any

from flask import Flask, g, redirect, url_for, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from .models import db, User, Post


class SecureModelView(ModelView):
    """ログイン済み かつ 管理者だけ通す ModelView。"""
    def is_accessible(self) -> bool:
        return g.get("user") is not None and g.user.is_admin

    def inaccessible_callback(self, name: str, **kwargs: Any):
        # 権限が無ければログインへ（API のログインエンドポイント）
        return redirect(url_for("auth.login", next=request.url))


def init_admin(app: Flask) -> None:
    admin = Admin(app, name="Flaskr Admin", url="/admin")
    # ★ Flask-Admin 2.x は ModelView(モデル, db)（db.session ではない）
    admin.add_view(SecureModelView(User, db))
    admin.add_view(SecureModelView(Post, db))
```

ファクトリ（`flaskr/__init__.py`）の `return app` 直前で呼ぶ:
```python
    from . import admin
    admin.init_admin(app)
```

## B-3. 自分を管理者にする

初期状態は誰も管理者ではないので、DB で 1 人昇格させます（[Step 0.5 の DB 接続](./00-docker-uv-mysql.md)参照）:
```bash
docker compose exec db mysql -uflaskr -pflaskr flaskr \
  -e "UPDATE user SET is_admin = 1 WHERE username = 'test';"
```

## 🧠 解説

- `is_accessible()` … このビューを表示してよいか毎回判定。あなたの `@bp.before_app_request`（`g.user` をセット）が `/admin` にも効くので、`g.user.is_admin` で判定できる
- `inaccessible_callback()` … 弾かれた時の挙動（ログインへリダイレクト）。メニューにも表示されなくなる
- **セッション Cookie を API と共有**するので、API でログイン → そのまま `/admin` も通る（同じ認証基盤）
- Flask-Admin は **HTML をサーバレンダリング**する。React SPA とは別 UI だが、管理は内部用途なのでこれで十分（`SECRET_KEY` によるフォーム CSRF 保護も効く）

## 🔮 予測 → 動作確認

**実行前に予想してみよう:** 未ログインで `/admin/user/` を開くと？ 管理者だと？

- 未ログイン → **302**（ログインへリダイレクトで弾かれる）
- 一般ユーザー → **302**（管理者でないので弾かれる）
- 管理者（`is_admin=1`）→ **200**（一覧が見える。作成・編集・削除も可能）

ブラウザで確認するなら、API でログイン（Cookie 取得）してから `http://localhost:5000/admin/` を開きます。

## つまずきポイント（Part B）

| 症状 | 原因・対処 |
|---|---|
| 誰でも `/admin` に入れてしまう | `is_accessible()` を実装していない/常に True。必ず `g.user.is_admin` で絞る |
| `DeprecationWarning: session ...` | `ModelView(User, db.session)` になっている。`ModelView(User, db)` に |
| `no such column: is_admin` | 列追加後に `init-db` していない。`uv run flask --app flaskr init-db` |
| 管理者にしても弾かれる | まだ**ログインしていない**（Cookie が無い）。API で login してから /admin |
| フォーム送信で CSRF エラー | `SECRET_KEY` が未設定/未読込。`.env` の `SECRET_KEY` を確認 |

## ✅ 想起チェック（Part B）

**見ないで説明してみよう:** Flask-Admin を安全に使うために最低限やるべきことは？

<details><summary>解答例</summary>

**認可（`is_accessible()`）を必ず実装して、管理者だけに絞る**こと。無認証で `/admin` を晒すと、誰でも全データを CRUD できてしまう。`User` に `is_admin` 列を持たせ、`is_accessible()` で「ログイン済み かつ `g.user.is_admin`」を要求し、外れたら `inaccessible_callback()` でログインへ逃がす。セッション Cookie は API と共有される。
</details>

---

## まとめ

- **APIFlask**: `Flask`→`APIFlask`、`@bp.input`/`@bp.output` でスキーマ化 → **検証・整形・ドキュメントが1つに**。`/docs`(Swagger UI)・`/openapi.json` が自動生成。デコレータ順序（`login_required` は外側）と `apiflask.abort(message=)`、`error_processor` が要点
- **Flask-Admin**: `ModelView(モデル, db)` を登録するだけで `/admin` に CRUD。**`is_accessible()` の認可が必須**
- どちらも**完成済み API への追加**。基礎（手動処理）を理解した上で自動化ツールへ移行、という順序が学びとして最適

これで「基礎 → REST API → フロント連携 → テスト → デプロイ → OpenAPI/管理画面」まで、実務スタックを一通り体験できました 🎉

← [目次に戻る](./README.md)
