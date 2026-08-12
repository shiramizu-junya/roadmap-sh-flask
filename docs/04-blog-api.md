# Step 4: 記事 CRUD API（認可付き）

← [Step 3](./03-auth-api.md) ／ [目次](./README.md) ／ 次: [Step 5](./05-testing.md)

## 🎯 目的

`blog` **Blueprint** を作り、記事の **一覧・作成・取得・更新・削除**（CRUD）を REST API で実装する。
「ログイン必須」と「著者本人のみ編集・削除可」の**認可**を効かせる。

> **核: `get_post` ヘルパーによる 404/403 の一元化**と、`login_required` + 著者チェックの認可。CRUD の骨格自体は Step3 の応用です。
> **補足: ルート設計**（`/posts` を一覧・作成に、`/posts/<id>` を取得・更新・削除に割り当てる REST 的な形）。

🔁 **置き換え**:
- 元記事は一覧取得で `JOIN user ... ORDER BY created DESC` を手書き → SQLAlchemy の `db.session.scalars(db.select(Post).order_by(...))` ＋ `to_dict()` で著者名込みの JSON にする
- 元記事の `@bp.route('/<int:id>/update')`（更新用ページ）は **`PUT /posts/<id>`** に、`/<id>/delete` は **`DELETE /posts/<id>`** に置き換え（HTTP メソッドで操作を表現するのが REST）
- 元記事の `app.add_url_rule('/', endpoint='index')` という小技は**不要**（`url_for` リダイレクトを使わないため）

このステップは**終盤なので、要件だけ示します。まず自力で書いてから**折りたたみの解答例と照合してください。

---

## 📋 要件

`flaskr/blog.py` を新規作成し、`blog` Blueprint（`url_prefix="/posts"`）に次を実装する。

**共通ヘルパー `get_post(id, check_author=True)`**
- `id` の記事を取得。無ければ **404**（`abort(404, ...)`）
- `check_author=True` かつ 著者が `g.user` でなければ **403**（`abort(403)`）
- 記事オブジェクトを返す

**エンドポイント**

| メソッド・パス | 認証 | 挙動 | 成功時 |
|---|---|---|---|
| `GET /posts` | 不要 | 全記事を作成日時の**降順**で返す | 200 + 配列 |
| `POST /posts` | 必須 | `title`（必須）・`body` を受け取り作成。著者は `g.user` | 201 + 作成した記事 |
| `GET /posts/<id>` | 不要 | 1件返す（著者チェックなし＝`check_author=False`） | 200 + 記事 |
| `PUT /posts/<id>` | 必須・著者のみ | `title`（必須）・`body` を更新 | 200 + 更新後の記事 |
| `DELETE /posts/<id>` | 必須・著者のみ | 削除 | 204（本文なし） |

- `title` が空なら **400** `{"error": "Title is required."}`
- Blueprint はファクトリで `register_blueprint` する（Step3 の `auth` と同じ要領。`return app` の直前に追記）

> ヒント（考え方のみ）:
> - `login_required` は Step3 で作った。`@bp.post(...)` の下に重ねて付ける（デコレータの順序: `@bp.route` が外側、`@login_required` が内側）
> - 更新/削除は先頭で `post = get_post(id)` を呼ぶだけで、404・403・ログイン判定がまとまる
> - 一覧は `db.session.scalars(db.select(Post).order_by(Post.created.desc())).all()` → 各要素を `to_dict()`
> - JSON ボディは `request.get_json(silent=True) or {}`（Step3 と同じ）

まず自分で書いてみましょう。書けたら下を開いて照合してください。

<details><summary>解答例（flaskr/blog.py 全体）</summary>

```python
from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import abort

from .auth import login_required
from .models import db, Post

bp = Blueprint("blog", __name__, url_prefix="/posts")


def get_post(id: int, check_author: bool = True) -> Post:
    """id の記事を取得。無ければ 404、著者違いなら 403。"""
    post = db.session.get(Post, id)

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post.author_id != g.user.id:
        abort(403)

    return post


@bp.get("")           # GET /posts
def index():
    posts = db.session.scalars(db.select(Post).order_by(Post.created.desc())).all()
    return jsonify([p.to_dict() for p in posts])


@bp.post("")          # POST /posts
@login_required
def create():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    body = data.get("body", "")

    if not title:
        return jsonify(error="Title is required."), 400

    post = Post(title=title, body=body, author_id=g.user.id)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_dict()), 201


@bp.get("/<int:id>")  # GET /posts/<id>
def show(id: int):
    post = get_post(id, check_author=False)
    return jsonify(post.to_dict())


@bp.put("/<int:id>")  # PUT /posts/<id>
@login_required
def update(id: int):
    post = get_post(id)                 # 404/403 をここで処理
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    body = data.get("body", "")

    if not title:
        return jsonify(error="Title is required."), 400

    post.title = title
    post.body = body
    db.session.commit()
    return jsonify(post.to_dict())


@bp.delete("/<int:id>")  # DELETE /posts/<id>
@login_required
def delete(id: int):
    post = get_post(id)                 # 404/403 をここで処理
    db.session.delete(post)
    db.session.commit()
    return "", 204
```

そして `flaskr/__init__.py` の `return app` の直前に:
```python
    from . import blog
    app.register_blueprint(blog.bp)
```
</details>

---

## 🧠 解説（照合後に読む）

**`get_post` が「重複排除 + 認可」の要**
更新も削除も「まず対象を取得 → 存在確認 → 著者確認」が共通。これを1関数に閉じ込めることで、各ビューは `post = get_post(id)` の1行で 404・403 を処理できます。元記事の設計思想をそのまま踏襲しています。

**`abort()` と JSON エラーの合流**
`abort(404, "...")` は `HTTPException` を投げます。Step3 でファクトリに登録した `@app.errorhandler(HTTPException)` がそれを捕まえ、`{"error": "..."}` の JSON + 対応ステータスに統一します。だから blog 側では `abort` を呼ぶだけでよい、という分担です。

**`GET /posts/<id>` だけ `check_author=False`**
閲覧は誰でも可、更新・削除は本人のみ。`check_author` 引数はこの差を1つの関数で吸収するためにあります（元記事のコメントと同じ意図）。

**デコレータの順序**
```python
@bp.post("")
@login_required
def create(): ...
```
外側（上）が `@bp.post`＝ルート登録、内側（下）が `@login_required`＝ログインガード。順序を逆にするとガードが効かないので注意。

> 🔗 **React との接続**: `login_required` は React の「認証ガード用の高階コンポーネント（`withAuth(Component)`）」と同じパターン。元の処理を包んで、条件を満たさなければ本体を実行させない。

---

## 🔮 予測 → 動作確認

**実行前に予想してみよう。**
- ログインせずに `POST /posts` したら？（`login_required` の挙動）
- 他人の記事を `DELETE` したら？（`get_post` の著者チェック）

```bash
# 事前に Step3 の cookie.txt でログイン済みとする（無ければ再ログイン）
curl -s -c cookie.txt -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" -d '{"username":"test","password":"test"}'

# 1) 未ログインで作成 → 401 を予想
curl -s -X POST http://127.0.0.1:5000/posts \
  -H "Content-Type: application/json" -d '{"title":"hi","body":"x"}'

# 2) ログイン状態で作成 → 201 を予想
curl -s -b cookie.txt -X POST http://127.0.0.1:5000/posts \
  -H "Content-Type: application/json" -d '{"title":"first post","body":"hello"}'

# 3) 一覧
curl -s http://127.0.0.1:5000/posts

# 4) 更新
curl -s -b cookie.txt -X PUT http://127.0.0.1:5000/posts/1 \
  -H "Content-Type: application/json" -d '{"title":"edited","body":"world"}'

# 5) 存在しない記事を更新 → 404 を予想
curl -s -b cookie.txt -X PUT http://127.0.0.1:5000/posts/999 \
  -H "Content-Type: application/json" -d '{"title":"x"}'
```

期待される出力（順に）:
```json
{"error":"Login required."}
{"id":1,"title":"first post","body":"hello","created":"...","author_id":1,"username":"test"}
[{"id":1,"title":"first post",...}]
{"id":1,"title":"edited","body":"world","created":"...","author_id":1,"username":"test"}
{"error":"Post id 999 doesn't exist."}
```
- 1) 401（`login_required`）／ 2) 201（作成成功）／ 5) 404（`abort(404)` → JSON エラー）

> 💡補足: 403 を体感するには、別ユーザーを登録・ログインして他人の記事を `PUT/DELETE` してみてください（`{"error":"Forbidden"}` が 403 で返る）。Step5 のテストでも検証します。

---

## ✅ 想起チェック

**見ないで説明してみよう:** `update` と `delete` の両方が先頭で `get_post(id)` を呼ぶだけで、「存在しない → 404」「他人の記事 → 403」「未ログイン → 401」の3つを処理できるのはなぜ？

<details><summary>解答例</summary>

- **401** は `@login_required` デコレータが `get_post` より前（外側）で処理する（`g.user` が無ければ即 401）。
- **404 / 403** は `get_post` の中で処理する。存在しなければ `abort(404)`、`check_author=True` で著者が `g.user` と違えば `abort(403)`。
- `abort` が投げる `HTTPException` はファクトリの `errorhandler` が JSON に整形する。
結果として各ビューは「`post = get_post(id)` を呼ぶ」だけで3種の失敗を一括でカバーできる。
</details>

**小問:** 元記事では更新は `/<id>/update`、削除は `/<id>/delete` という**別 URL**だった。REST 版ではなぜ URL を `/posts/<id>` に統一し、メソッドで分けたのか？

<details><summary>解答例</summary>

REST では「**リソース**（`/posts/<id>` という記事1件）を URL で表し、それに対する**操作**を HTTP メソッド（取得=GET / 更新=PUT / 削除=DELETE）で表す」設計が基本だから。URL は名詞（リソース）、メソッドが動詞（操作）という役割分担になり、API がシンプルで予測しやすくなる。
</details>

---

次は [Step 5: pytest でテスト](./05-testing.md)。
