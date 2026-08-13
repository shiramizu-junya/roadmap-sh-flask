# 発展ステップ: スキーマと OpenAPI（spectree で Swagger UI + React 型の自動生成）

← [Step 7](./07-wrapup.md) ／ [目次](./README.md)

**作るもの**: Pydantic スキーマで**入力バリデーション**と**出力シリアライズ**を一元化し、**Swagger UI** を自動生成、さらに **React の TS 型を自動生成**する
**重要度**: 🔴 **毎日書く**（スキーマ駆動は実務REST APIの標準。手書きの検証/変換を置き換える）
**前提**: Step 3（auth）・Step 4（posts CRUD）が動いていること
**なぜ「発展」に置くか**: まず Step 3/4 で**手書き**（`if not title:` や `post_to_dict`）を経験したうえで、その手作業を標準ツールで置き換えると「何が自動化されるか」が腹落ちするため

> 🔁 **置き換え**:
> - Step 3/4 の**手書きバリデーション**（`if not title or not body:`）→ **Pydantic スキーマ**
> - Step 4 の**手書きシリアライズ**（`post_to_dict`）→ **Pydantic の `model_validate` / `model_dump`**
> - README の**手書きAPI表** → **自動生成される Swagger UI / OpenAPI**
> - Step 6 の**手書き TS 型**（`type Post = {...}`）→ **openapi-typescript で自動生成**

---

## 8-1. これで何が変わるか（Before → After）

| 観点 | Before（Step 3/4 の手書き） | After（このステップ） |
|---|---|---|
| 入力チェック | 各ルートで `if not title: return ..., 400` を都度書く | スキーマ定義1つ。違反は**自動で 422** |
| 出力の形 | `post_to_dict` を手で組み、列追加時に直し忘れる | スキーマから `model_dump` で自動 |
| API仕様書 | README に手書きの表 | `/apidoc/swagger` に**自動生成 Swagger UI** |
| React の型 | Step 6 で手書き `type Post` | OpenAPI から**自動生成**、サーバーとズレない |

> 🧠 **考え方**: 「**入出力の形（スキーマ）を1箇所で宣言**すれば、検証・変換・ドキュメント・フロントの型が**すべてそこから導出**される」。
> これが“スキーマ駆動開発”。あなたが TS で型を中心に組むのと同じ発想を、API 境界に持ち込む。

> ⚠️ **超重要な区別（再掲）**: **ORM モデル（`models.py` の `User`/`Post`）** と **スキーマ（Pydantic）** は別物。
> - ORM モデル = **DBのテーブル**の形
> - スキーマ = **APIの入出力（JSON）**の形
> 似ているが役割が違うので**別ファイル**に分ける。`models.py` は一切変更しない。

---

## 8-2. spectree を入れる

```bash
# flaskr-api/ の中で
uv add spectree
```

| ライブラリ | 役割 |
|---|---|
| `spectree` | Pydantic スキーマから **バリデーション + OpenAPI + Swagger UI** を生やす。Pydantic は spectree が依存で入れる |

> 💡 **補足**: spectree は「Flask のルートに `@spec.validate(...)` を貼るだけ」で、入力検証・エラー応答(422)・OpenAPI生成を全部やる薄い層。FastAPI 的な体験を Flask に足すもの。

---

## 8-3. スキーマを定義する（コード全文・写経）

`flaskr/schemas.py` を新規作成します。**`models.py` とは別ファイル**です。

**ファイル: `flaskr-api/flaskr/schemas.py`（全文）**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---- 出力スキーマ（APIが返すJSONの形）----
class UserOut(BaseModel):
    # ORM オブジェクト（属性アクセス）から変換できるようにする
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    created: datetime
    author: UserOut


# ---- 入力スキーマ（APIが受け取るJSONの形）----
class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1)


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8)
```

### 🔬 構文解剖: `class UserOut(BaseModel):`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `BaseModel` | ベースモデル | Pydantic の基底クラス。継承すると「型注釈がそのままスキーマになる」 |
| `id: int` | — | **型注釈だけで列（フィールド）定義**。`int` 必須フィールド。TS の `id: number` と同じ感覚 |

**既知スタックとの対応**: **TS の `interface`／`type` とほぼ同じ**。`class PostIn(BaseModel): title: str` は `interface PostIn { title: string }` に相当。
違いは、Pydantic は**実行時にも検証する**（TS の型は実行時に消えるが、Pydantic は届いた JSON が型に合うか実際にチェックする）。
**なぜ SQLAlchemy の `Mapped[int]` と書き方が違うのか**: あちらは「DB列」、こちらは「JSONフィールド」。土台が別（`db.Model` vs `BaseModel`）なので書き方も別。役割が違うことの表れ。

### 🔬 構文解剖: `model_config = ConfigDict(from_attributes=True)`

| 部品 | 意味 |
|---|---|
| `model_config` | Pydantic v2 でモデルの設定を書く特別な属性名 |
| `ConfigDict(...)` | 設定を作る関数 |
| `from_attributes=True` | **辞書だけでなく「属性を持つオブジェクト」からも変換可**にする。＝**ORM の `Post` インスタンスをそのまま渡せる** |

**なぜ必要か**: 後で `PostOut.model_validate(post)` のように **SQLAlchemy の `Post` オブジェクトを直接**スキーマに変換したい。既定では辞書しか受けないが、`from_attributes=True` で `post.title` のような**属性読み取り**を許可する。これが `post_to_dict` を消せる鍵。
**既知スタックとの対応**: TS には無い（実行時変換の概念）。あえて言えば DTO へのマッピング設定。

### 🔬 構文解剖: `title: str = Field(min_length=1, max_length=120)`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `= Field(...)` | フィールド | フィールドに**制約や既定値**を付ける関数。型注釈に条件を足す |
| `min_length=1` | — | 最小1文字。**空文字を弾く**（Step 4 の `if not title:` の代わり） |
| `max_length=120` | — | 最大120文字。`models.py` の `String(120)` と揃える |

**効果**: 入力がこの制約を破ると、spectree が**自動で `422 Unprocessable Entity`** を返す（自分で `if` を書かない）。
**既知スタックとの対応**: zod の `z.string().min(1).max(120)` とほぼ同じ発想（TS のスキーマバリデーション）。
**なぜ `String(120)` と揃えるか**: DB列の上限を超える入力を、DBに届く前にAPI層で弾くため。二重の防御。

---

## 8-4. spectree を `create_app` に登録する（差分）

**ファイル: `flaskr-api/flaskr/__init__.py`（追加する差分）**

```python
from spectree import SpecTree  # ★追加（ファイル冒頭の import 群へ）

# create_app の外（モジュール直下）に1個作る
spec = SpecTree("flask", title="Flaskr API", version="1.0.0")


def create_app(test_config=None):
    app = Flask(__name__)
    # ...（既存の設定・db.init_app・CORS・Blueprint 登録はそのまま）...

    from .auth import bp as auth_bp
    from .posts import bp as posts_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)

    spec.register(app)  # ★追加：Blueprint 登録の「後」に置く（全ルートを走査するため）

    return app
```

### 🔬 構文解剖: `spec = SpecTree("flask", ...)` と `spec.register(app)`

| 部品 | 意味 |
|---|---|
| `SpecTree("flask", ...)` | Flask 用の spectree インスタンス。`title`/`version` は Swagger に出るAPI名 |
| モジュール直下に作る | `@spec.validate` を各ルートで使うため、`db` と同じく共有インスタンスにする |
| `spec.register(app)` | アプリの全ルートを走査して OpenAPI を組み、`/apidoc/*` を生やす |

**なぜ `register` を Blueprint 登録の後に置くか**: `register` は**その時点で登録済みのルート**から仕様を作る。Blueprint より先に呼ぶと、posts/auth のルートが仕様に載らない。**順番が重要**。
**既知スタックとの対応**: `db.init_app(app)` と同じ「共有インスタンスを後からアプリに結ぶ」パターン（Step 2）。

---

## 8-5. ルートをスキーマ方式に置き換える（Step 4 の refactor）

Step 4 の `create` を、手書き検証＋`post_to_dict` から**スキーマ方式**に置き換えます。

**Before（Step 4）:**
```python
@bp.post("")
@login_required
def create():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    body = data.get("body")
    if not title or not body:                 # 手書き検証
        return {"error": "title and body are required"}, 400
    post = Post(title=title, body=body, author_id=g.user.id)
    db.session.add(post)
    db.session.commit()
    return post_to_dict(post), 201            # 手書きシリアライズ
```

**After（このステップ）:**
```python
from flask import request
from spectree import Response

from . import spec                     # __init__.py の spec を使う
from .schemas import PostIn, PostOut


@bp.post("")
@login_required
@spec.validate(json=PostIn, resp=Response(HTTP_201=PostOut, HTTP_401=None))
def create():
    data = request.context.json        # 検証済みの PostIn インスタンス
    post = Post(title=data.title, body=data.body, author_id=g.user.id)
    db.session.add(post)
    db.session.commit()
    return PostOut.model_validate(post).model_dump(), 201
```

### 🔬 構文解剖: `@spec.validate(json=PostIn, resp=Response(HTTP_201=PostOut, HTTP_401=None))`

| 部品 | 意味 |
|---|---|
| `@spec.validate(...)` | このルートの**入力/出力スキーマ**を宣言するデコレータ。検証と仕様生成を担う |
| `json=PostIn` | **リクエストボディ**を `PostIn` で検証。違反時は**自動で 422** |
| `resp=Response(...)` | 返しうるレスポンスの種類。Swagger に「何が返るか」を載せる |
| `HTTP_201=PostOut` | 成功時 201 で `PostOut` を返す、と宣言 |
| `HTTP_401=None` | 401 も返しうる（本文スキーマなし）。`login_required` の 401 を仕様に明記 |

**デコルータの重ね順**: `@bp.post("")` → `@login_required` → `@spec.validate(...)` の順。ルート登録が一番外、ログイン確認、スキーマ検証、と外側から包む。
**既知スタックとの対応**: `@spec.validate` は「ルートに型契約を貼る」。tRPC や zod ミドルウェアでハンドラの入出力を型で縛るのに近い。

### 🔬 構文解剖: `data = request.context.json`

| 部品 | 意味 |
|---|---|
| `request.context` | spectree が検証結果を入れる置き場（`.json` / `.query` / `.headers`） |
| `.json` | ボディを検証済みの **`PostIn` インスタンス**として取得。`data.title` と**属性アクセス** |

**Before との違い**: `request.get_json()`（生の辞書、未検証）→ `request.context.json`（型付き・検証済み）。`data.get("title")` の防御的取り出しが不要になる。
**なぜ属性アクセスか**: Pydantic インスタンスなので `data["title"]` ではなく `data.title`。IDE 補完も効く。

### 🔬 構文解剖: `PostOut.model_validate(post).model_dump()`

| 部品 | 意味 |
|---|---|
| `PostOut.model_validate(post)` | **ORM の `post` を `PostOut` に変換**（`from_attributes=True` のおかげ）。`post.author` も `UserOut` に自動変換 |
| `.model_dump()` | Pydantic インスタンス → **辞書**に変換。Flask が JSON 化して返す |

**これで `post_to_dict` が消える**: 手書きの変換関数が不要に。列を足したらスキーマに足すだけで、入出力・ドキュメント・型が一斉に追従する。
**`model_dump()` と `model_dump_json()`**: 前者は辞書（Flask に返す用）、後者は JSON 文字列。ここは Flask が辞書を JSON 化するので `model_dump()` を使う。`datetime` は自動で ISO 文字列になる。

### 課題（フェード・自力）: `index` と auth を置き換える

**要件:**
1. `GET /posts`（`index`）を `@spec.validate(resp=Response(HTTP_200=list[PostOut]))` にし、`[PostOut.model_validate(p).model_dump() for p in posts]` を返す
2. `POST /auth/register` と `POST /auth/login` を `json=Credentials` で検証し、手書きの `if not username or not password:` を消す

**判定基準:** 空 title の作成が **422**、8文字未満パスワードの register が **422**、`/apidoc/swagger` に全ルートが出る。

<details><summary>解答例（要点）</summary>

```python
# posts.py
@bp.get("")
@spec.validate(resp=Response(HTTP_200=list[PostOut]))
def index():
    posts = db.session.scalars(
        db.select(Post).order_by(Post.created.desc())
    ).all()
    return [PostOut.model_validate(p).model_dump() for p in posts], 200
```

```python
# auth.py
from .schemas import Credentials, UserOut

@bp.post("/register")
@spec.validate(json=Credentials, resp=Response(HTTP_201=UserOut, HTTP_409=None))
def register():
    data = request.context.json          # 検証済み（8文字未満は自動422）
    exists = db.session.scalar(db.select(User).filter_by(username=data.username))
    if exists is not None:
        return {"error": "username already taken"}, 409
    user = User(username=data.username,
                password_hash=generate_password_hash(data.password))
    db.session.add(user)
    db.session.commit()
    return UserOut.model_validate(user).model_dump(), 201
```
（`min_length=8` をスキーマに入れたので、Step 7 宿題の「パスワード長チェック」も自動で満たされる）
</details>

---

## 8-6. 🔮 予測 → 動作確認（Swagger UI）

前提: MySQL 起動・`init-db` 済み・サーバー起動（`--port 5001`）。

### 🔮 実行前に予想しよう
1. 空の `title` で `POST /posts` すると何番？（Step 4 では 400 だった。今は？）
2. Swagger UI はどの URL で見える？

### 動作確認

ブラウザで **`http://127.0.0.1:5001/apidoc/swagger/`**（末尾スラッシュ）を開く。

- 全エンドポイントが一覧表示され、各スキーマ（PostIn/PostOut など）が見える
- 「Try it out」でブラウザから直接 API を叩ける

curl でも:
```bash
# 空 title → 自動 422
curl -i -X POST http://127.0.0.1:5001/posts \
  -H "Content-Type: application/json" -d '{"title":"","body":"x"}' -b alice.txt

# OpenAPI 仕様（JSON）を取得
curl -s http://127.0.0.1:5001/apidoc/openapi.json | head -c 200
```

### 期待される結果
- 空 title → **422**（予想1。手書き 400 → スキーマ 422 に変わった）
- Swagger UI が `/apidoc/swagger/` に表示（予想2）
- `/apidoc/openapi.json` が仕様 JSON を返す

---

## 8-7. React の TS 型を OpenAPI から自動生成する（Step 6 の置き換え）

Step 6 では `type Post = {...}` を**手書き**しました。これを OpenAPI から**自動生成**します。

```bash
# frontend/ で。サーバー（:5001）を起動した状態で実行
npx openapi-typescript http://127.0.0.1:5001/apidoc/openapi.json -o src/api-types.ts
```

### 🔬 構文解剖: `npx openapi-typescript <URL> -o <出力>`

| 部品 | 意味 |
|---|---|
| `npx openapi-typescript` | OpenAPI(JSON) から TS 型を生成するツール（都度DLして実行） |
| `<URL>` | 先ほどの `/apidoc/openapi.json` |
| `-o src/api-types.ts` | 出力先ファイル |

**効果**: `PostOut`/`PostIn` などが `src/api-types.ts` に**TS型として生成**される。サーバーのスキーマを変えて再生成すれば、フロントの型が**必ず追従**する（手書きのズレが消える）。
**既知スタックとの対応**: GraphQL Code Generator の REST 版。スキーマ→型の自動生成という同じ発想。

> 🏢 **実務メモ**: この生成を `package.json` の `scripts`（例 `"gen:api": "openapi-typescript ..."`）に入れ、CI やコミット前に走らせる。サーバーとフロントの型契約を機械で保証できる。

---

## 8-8. 🏢 実務メモ / ⚠️ アンチパターン

### 🏢 実務メモ
入力・出力で**別スキーマ**に分けるのが定石（`PostIn` は `id`/`created` を受けない、`PostOut` は `password` を絶対返さない）。
「受け取ってよい形」と「返してよい形」は違う。1つのスキーマで兼用すると、`id` を書き換えられる等の事故につながる。

### ⚠️ やりがち
> **やりがち**: ORM モデル（`Post`）を Pydantic スキーマ代わりに直接返そうとして、`password_hash` など**返してはいけない列**まで露出する。
> **現場では**: 出力は必ず**出力専用スキーマ（`PostOut`/`UserOut`）を経由**させ、返す列を明示する。`model_validate(orm).model_dump()` が安全な変換口。

---

## 8-9. ✅ 想起チェック

<details><summary>Q1. ORM モデル（`db.Model`）と Pydantic スキーマ（`BaseModel`）の役割の違いは？</summary>

ORM モデル＝DBテーブルの形、Pydantic スキーマ＝APIの入出力(JSON)の形。土台が別（`db.Model` vs `BaseModel`）で、別ファイルに分ける。`models.py` は変更しない。
</details>

<details><summary>Q2. `from_attributes=True` は何のため？</summary>

Pydantic が辞書だけでなく「属性を持つオブジェクト」からも変換できるようにする設定。これで `PostOut.model_validate(orm_post)` のように ORM インスタンスを直接スキーマ化でき、`post_to_dict` が不要になる。
</details>

<details><summary>Q3. `spec.register(app)` を Blueprint 登録の後に置くのはなぜ？</summary>

register はその時点で登録済みのルートから OpenAPI を作るため。Blueprint より先だと posts/auth のルートが仕様に載らない。
</details>

<details><summary>Q4. スキーマ違反（空 title 等）のとき、誰がどのステータスを返す？</summary>

spectree が自動で `422 Unprocessable Entity` を返す。自分で `if` を書かなくてよい。
</details>

---

## ✍️ ブランクページ（章末の再現）

`schemas.py` を閉じて白紙から再現:
- `UserOut` / `PostOut`（`model_config = ConfigDict(from_attributes=True)` + フィールド、`author: UserOut` の入れ子）
- `PostIn` / `Credentials`（`Field(min_length=...)`）

さらに、`create` ルートを `@spec.validate(json=..., resp=Response(...))` + `request.context.json` + `model_validate(...).model_dump()` の形で書けるか試す。

---

## まとめ

- **スキーマ（Pydantic）を1箇所で宣言**すれば、検証・シリアライズ・API仕様・フロント型が全部そこから導出される
- ORM モデルとスキーマは**別物・別ファイル**（`models.py` は触らない）
- `@spec.validate(json=..., resp=Response(...))` + `request.context.json` で**手書き検証を廃止**（違反は自動 422）
- `PostOut.model_validate(orm).model_dump()` で**手書き `post_to_dict` を廃止**（`password_hash` 露出も防ぐ）
- `/apidoc/swagger/` に **Swagger UI 自動生成**、`openapi-typescript` で **React の型を自動生成**

これで「手書き」だった検証・変換・ドキュメント・フロント型が、**スキーマ1点から自動導出**される構成になりました。
