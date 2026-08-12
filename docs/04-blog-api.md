# Step 4: ブログ CRUD API（一覧・作成・取得・更新・削除 + 認可）

← [Step 3](./03-auth-api.md) ／ [目次](./README.md) ／ 次: [Step 5](./05-testing.md)

**作るもの**: `posts` Blueprint で `GET/POST /posts`、`GET/PUT/DELETE /posts/<id>` を実装（更新・削除は**著者本人のみ**）
**重要度**: 🔴 **毎日書く**（CRUD + 認可は業務APIの中心）
**前ステップとの接続**: Step 2 の `Post` モデルと Step 3 の `g.user`/`login_required` を組み合わせる

> このステップは**フェード終盤**です。前半は完成コード、後半（更新・削除）は**要件だけ提示 → 自力 → 折りたたみで答え合わせ**にします。

---

## 4-1. 一覧・作成・取得（完成コード）

**ファイル: `flaskr-api/flaskr/posts.py`（前半・完成形）**

```python
from flask import Blueprint, abort, g, request

from .auth import login_required
from .models import Post, db

bp = Blueprint("posts", __name__, url_prefix="/posts")


def post_to_dict(post):
    """Post を JSON 用の辞書へ変換する。"""
    return {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "created": post.created.isoformat(),
        "author": {"id": post.author.id, "username": post.author.username},
    }


def get_post_or_404(post_id):
    """id で1件取得。無ければ 404 で打ち切る。"""
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404, description="post not found")
    return post


@bp.get("")
def index():
    posts = db.session.scalars(
        db.select(Post).order_by(Post.created.desc())
    ).all()
    return [post_to_dict(p) for p in posts], 200


@bp.post("")
@login_required
def create():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    body = data.get("body")

    if not title or not body:
        return {"error": "title and body are required"}, 400

    post = Post(title=title, body=body, author_id=g.user.id)
    db.session.add(post)
    db.session.commit()
    return post_to_dict(post), 201


@bp.get("/<int:post_id>")
def show(post_id):
    post = get_post_or_404(post_id)
    return post_to_dict(post), 200
```

---

## 4-2. 🔬 構文解剖

### 🔬 構文解剖: `from flask import ..., abort, ...`

| 部品 | 意味 |
|---|---|
| `abort(404, description=...)` | 処理を**その場で中断**し、指定ステータスのエラー応答を発生させる |

**なぜ `return` でなく `abort` か**: 途中の関数（`get_post_or_404`）から、呼び出し元まで戻らず**一気にエラー応答を返したい**とき。例外を投げる仕組みで実現している。
**既知スタックとの対応**: Express の `next(createError(404))` に近い。深い所からエラーを投げ上げる。

### 🔬 構文解剖: `post.created.isoformat()`

| 部品 | 意味 |
|---|---|
| `post.created` | `DateTime` 列の値（Python の `datetime` オブジェクト） |
| `.isoformat()` | ISO 8601 文字列（`"2026-08-12T09:30:00"`）に変換 |

**なぜ変換するか**: `datetime` はそのままでは JSON にできない。文字列化して返す。フロント(JS)は ISO 文字列を `new Date(...)` で受けやすい。

### 🔬 構文解剖: `@bp.get("")`（空パス）

| 部品 | 意味 |
|---|---|
| `""` | 空パス。Blueprint の `url_prefix="/posts"` と合わさり `GET /posts` になる |

**なぜ空文字か**: prefix が既に `/posts`。ここで `"/"` と書くと `/posts/` になり末尾スラッシュ有無で分かれる。一覧は `/posts` にしたいので空にする。

### 🔬 構文解剖: `db.select(Post).order_by(Post.created.desc())`

| 部品 | 意味 |
|---|---|
| `.order_by(...)` | 並び順の指定（SQL の `ORDER BY`） |
| `Post.created.desc()` | `created` 列の**降順**（新しい順）。`.desc()` は descending |
| `db.session.scalars(...).all()` | 複数件を取り出しリスト化。`scalar`(単数)との違いに注意 |

**既知スタックとの対応**: Prisma の `findMany({ orderBy: { created: "desc" } })`。

### 🔬 構文解剖: リスト内包表記 `[post_to_dict(p) for p in posts]`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `[式 for 変数 in 反復可能]` | — | **リスト内包表記**。ループを1行で書き、新しいリストを作る |
| `for p in posts` | — | `posts` を1つずつ `p` に取り出す |
| `post_to_dict(p)` | — | 各要素に適用する式 |

**既知スタックとの対応**: JS の `posts.map(p => postToDict(p))` とほぼ同じ。Python で頻出の書き方なので手に馴染ませる。
**なぜ使うか**: 「各モデルを辞書に変換したリスト」を簡潔に作れる。API の一覧レスポンスの定番。

### 🔬 構文解剖: `@bp.post("")` と `@login_required` の**重ねがけ**

```python
@bp.post("")
@login_required
def create():
    ...
```

| 部品 | 意味 |
|---|---|
| デコレータを2段 | 上から順に外側→内側で包む。`create` はまず `login_required` で包まれ、その結果がルート登録される |
| 効果 | 「ログイン必須」かつ「`POST /posts` で呼ばれる」関数になる |

**順番の意味**: `@bp.post("")` を上に、`@login_required` を下（関数に近い側）に置く。ルート登録は「ログインチェック済みの関数」を登録したいので、`login_required` が関数に近い方。

### 🔬 構文解剖: `@bp.get("/<int:post_id>")`（URL 変数と型変換）

| 部品 | 読み方 | 意味 |
|---|---|---|
| `<...>` | 山カッコ | URL の**動的な部分**を捕まえる。`/posts/5` の `5` を取る |
| `int:` | イント | **コンバータ**。文字列を整数に変換し、整数でなければ 404。無いと文字列のまま |
| `post_id` | — | 捕まえた値が渡る**引数名**。関数の引数名と一致させる（`def show(post_id):`） |

**既知スタックとの対応**: Express の `/posts/:id` + `req.params.id`。Flask は `<int:post_id>` と書くだけで**型変換とバリデーションが同時**にできる。
**なぜ `int:` を付けるか**: `id` は整数。`/posts/abc` のような不正を Flask 側で弾ける（付けないと文字列で入ってくる）。

---

## 4-3. 更新・削除（要件のみ → 自力 → 解答）

ここからは**あなたが書く番**です。前半のコードと Step 3 を組み合わせれば書けます。

### 課題: `PUT /posts/<id>`（更新）

**要件:**
- `@login_required` を付ける
- `get_post_or_404(post_id)` で対象を取得
- **著者本人でなければ `403 Forbidden`**（`{"error": "forbidden"}`）で拒否
  - 判定: `post.author_id != g.user.id`
- ボディの `title` / `body` があれば更新（両方必須なら 400）
- `db.session.commit()` して、更新後を `post_to_dict` で 200 返却

**判定基準（自分で検証）:**
- 他人の記事を更新しようとすると `403`
- 本人が正しいボディで更新すると `200` + 更新後 JSON
- `title` を空で送ると `400`

<details><summary>解答例</summary>

```python
@bp.put("/<int:post_id>")
@login_required
def update(post_id):
    post = get_post_or_404(post_id)
    if post.author_id != g.user.id:
        return {"error": "forbidden"}, 403

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    body = data.get("body")
    if not title or not body:
        return {"error": "title and body are required"}, 400

    post.title = title
    post.body = body
    db.session.commit()
    return post_to_dict(post), 200
```

**ポイント**: 取得したモデルの属性(`post.title`)を代入で書き換え、`commit` するだけで UPDATE が走る（SQLAlchemy が変更を追跡している）。個別に UPDATE 文を書く必要はない。
</details>

### 課題: `DELETE /posts/<id>`（削除）

**要件:**
- `@login_required`
- `get_post_or_404` で取得
- 著者本人でなければ `403`
- `db.session.delete(post)` → `commit`
- 本文なし `204` を返す

**判定基準:**
- 他人の記事削除は `403`
- 本人が削除すると `204`、その後 `GET /posts/<id>` は `404`

<details><summary>解答例</summary>

```python
@bp.delete("/<int:post_id>")
@login_required
def destroy(post_id):
    post = get_post_or_404(post_id)
    if post.author_id != g.user.id:
        return {"error": "forbidden"}, 403

    db.session.delete(post)
    db.session.commit()
    return "", 204
```

</details>

---

## 4-4. 404 を JSON で返す（エラーハンドラ）

`abort(404)` の既定レスポンスは HTML です。REST API なので**JSON で返す**よう `create_app` に整えます。

**ファイル: `flaskr-api/flaskr/__init__.py` に追記（差分）**

```python
    # ★追加：エラーを JSON で返す
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return {"error": e.description, "status": e.code}, e.code
```

そして posts Blueprint を登録:

```python
    from .posts import bp as posts_bp
    app.register_blueprint(posts_bp)
```

### 🔬 構文解剖: `@app.errorhandler(HTTPException)`

| 部品 | 意味 |
|---|---|
| `@app.errorhandler(型)` | 指定した**例外型が投げられたとき**に呼ぶハンドラを登録 |
| `HTTPException` | Flask/werkzeug の HTTP エラーの基底クラス（404,403,400… の親） |
| `e.description` / `e.code` | 例外が持つ説明文とステータス番号 |

**効果**: `abort(404, description="post not found")` が投げた例外を捕まえ、`{"error":"post not found","status":404}` を 404 で返す。API全体でエラー形式を JSON に統一できる。
**既知スタックとの対応**: Express のエラーミドルウェア `app.use((err,req,res,next)=>...)` に相当。

---

## 4-5. 🏢 実務メモ / ⚠️ アンチパターン

### 🏢 実務メモ
「**取得 → 権限チェック → 変更 → commit**」の順序は CRUD の定型。特に**権限チェックを変更の前に必ず置く**。
一覧APIは将来データが増えると重くなるため、実務では**ページネーション**（`limit`/`offset` や cursor）を最初から入れることが多い（本ステップの発展課題で扱う）。

### ⚠️ やりがち
> **やりがち**: 一覧で `post.author.username` を各記事ごとに参照し、記事数だけ追加クエリが飛ぶ（**N+1問題**）。
> **現場では**: `db.select(Post).options(db.joinedload(Post.author))` のように**関連をまとめて取得**して1〜数クエリに抑える。まずは動かし、計測して必要なら最適化する。

---

## 4-6. 🔮 予測 → 動作確認

前提: サーバー起動、`alice` で登録済み（Step 3）。

### 🔮 実行前に予想しよう
1. ログインせずに `POST /posts` すると何番？
2. `alice` の記事を、別ユーザー `bob` で `PUT` すると何番？
3. `GET /posts` の返り値の**型**は？（オブジェクト？配列？）

### 動作確認

```bash
# alice でログイン（Cookie 保存）
curl -s -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pw12345"}' -c alice.txt

# 記事作成（Cookie 送信）
curl -i -X POST http://127.0.0.1:5000/posts \
  -H "Content-Type: application/json" \
  -d '{"title":"最初の記事","body":"本文です"}' -b alice.txt

# 一覧
curl -s http://127.0.0.1:5000/posts

# ログインなしで作成 → 401
curl -i -X POST http://127.0.0.1:5000/posts \
  -H "Content-Type: application/json" \
  -d '{"title":"x","body":"y"}'
```

### 期待される要点
- 作成: `201` + 記事JSON（`author` に alice）
- 一覧: `200` + **配列**`[ {...} ]`（予想3）
- 未ログイン作成: `401`（予想1）
- 別人の更新: `403`（予想2。bob を登録・ログインして試す）

---

## 4-7. ✅ 想起チェック

<details><summary>Q1. `<int:post_id>` の `int:` は何をする？</summary>

URL の該当部分を整数に変換して引数へ渡す。整数でなければ 404。バリデーションと型変換を同時に行う。
</details>

<details><summary>Q2. 取得したモデルの属性に代入して `commit` するだけで UPDATE が走るのはなぜ？</summary>

SQLAlchemy のセッションが読み込んだオブジェクトの変更を追跡しており、`commit` 時に変更された列を UPDATE 文にして送るから。
</details>

<details><summary>Q3. 認可チェック（本人か）を、変更処理の「前」に置くのはなぜ？</summary>

権限のない変更を実行してしまう前に弾くため。後に置くと一瞬でも不正な変更が走るリスクや無駄な処理が生じる。
</details>

<details><summary>Q4. N+1 問題とは？回避策は？</summary>

一覧で各行の関連（author）を個別クエリで引き、行数分の追加クエリが飛ぶ問題。`joinedload` などで関連をまとめて取得して回避する。
</details>

---

## ✍️ ブランクページ（章末の再現）

`posts.py` を閉じて白紙から再現。特に:

- `post_to_dict`（`created.isoformat()`、`author` の入れ子）
- `index`（`order_by(...desc())` + リスト内包表記）
- `create`（`@login_required`、400、`author_id=g.user.id`、201）
- `update`/`destroy`（403 の本人判定、commit / delete）

---

## まとめ

- CRUD は「取得 → 認可 → 変更 → commit」。更新は**属性代入 + commit**だけで UPDATE
- URL 変数は `<int:post_id>`（型変換つき）、一覧は**リスト内包表記**で JSON 配列に
- `abort(404)` + `errorhandler(HTTPException)` で**エラーも JSON 統一**
- 認可は `post.author_id != g.user.id` で本人判定 → `403`

次の [Step 5](./05-testing.md) で、ここまでの API を **pytest** で自動テストします。
