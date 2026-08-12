# Step 3: 認証 API（Blueprint / セッション / ガード）

← [Step 2](./02-database-sqlalchemy.md) ／ [目次](./README.md) ／ 次: [Step 4](./04-blog-api.md)

## 🎯 目的

`auth` **Blueprint** を作り、登録・ログイン・ログアウト・「現在のユーザー」を **JSON API** として実装する。
さらに、後続ステップで使う **`login_required` デコレータ**（未ログインなら 401）を用意する。

> **核: セッション Cookie 認証の流れ**（`session["user_id"]` に保存 → `before_app_request` で毎回 `g.user` に復元 → `login_required` で保護）。ここが Flask 認証の心臓部です。
> **核: Blueprint によるルート分割。**
> **補足: パスワードハッシュの内部実装**（`generate_password_hash` を使うだけでOK）。

🔁 **置き換え**: 元記事は `flash()` でエラーを画面表示し、`redirect(url_for("index"))` でページ遷移していました。REST API では **`{"error": "..."}` の JSON + ステータスコード**を返し、遷移はフロントが担います。`request.form[...]` → **`request.get_json()`** も置き換えです。

このステップは**中盤なので骨組み + `# TODO` の穴埋め**です。`register` を手本に、残りを自力で埋めてください。

---

## 💻 コード

### 3-1. まず「土台」をファクトリに足す（CORS と JSON エラー）

`flaskr/__init__.py` の import 群に追記:

```python
from flask import jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
```

`create_app` の中、`return app` の**直前**に追記:

```python
    # React(5173) から Cookie 付きリクエストを許可する
    # 🔁 置き換え: 元記事は同一オリジンなので CORS 不要だった
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}},
         supports_credentials=True)

    # abort(404) などの HTTP 例外を JSON に統一して返す
    # 🔁 置き換え: 元記事はエラーページ(HTML)を返していた
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        return jsonify(error=e.description), e.code

    from . import auth
    app.register_blueprint(auth.bp)

    return app
```

### 3-2. 認証 Blueprint

`flaskr/auth.py` を新規作成:

```python
import functools
from collections.abc import Callable
from typing import Any

from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .models import db, User

# 'auth' Blueprint。すべての URL に /auth が前置される
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user() -> None:
    """全リクエストの前に走り、ログイン中ユーザーを g.user に載せる。"""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get(User, user_id)


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """未ログインなら 401 を返すデコレータ（Step4 の記事操作で使う）。"""
    @functools.wraps(view)
    def wrapped_view(**kwargs: Any) -> Any:
        # TODO(1): g.user が None なら {"error": "Login required."} を 401 で返す
        ...
        return view(**kwargs)
    return wrapped_view


# ---- 手本: 登録（この形をまねて login/logout/me を書く）----
@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username:
        return jsonify(error="Username is required."), 400
    if not password:
        return jsonify(error="Password is required."), 400
    if db.session.scalar(db.select(User).filter_by(username=username)) is not None:
        return jsonify(error=f"User {username} is already registered."), 400

    user = User(username=username, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify(id=user.id, username=user.username), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    user = db.session.scalar(db.select(User).filter_by(username=username))
    # TODO(2): user が None なら "Incorrect username." を 400 で返す
    # TODO(3): check_password_hash(user.password, password) が False なら
    #          "Incorrect password." を 400 で返す
    ...

    # 認証成功: セッションを作り直して user_id を保存する
    session.clear()
    session["user_id"] = user.id
    return jsonify(id=user.id, username=user.username)


@bp.post("/logout")
def logout():
    # TODO(4): セッションを空にして、本文なし・ステータス 204 を返す
    ...


@bp.get("/me")
def me():
    # TODO(5): g.user が None なら {"user": None}、
    #          いれば {"id":..., "username":...} を返す
    ...
```

<details><summary>解答例（TODO(1)〜(5)）</summary>

```python
# TODO(1)
    def wrapped_view(**kwargs: Any) -> Any:
        if g.user is None:
            return jsonify(error="Login required."), 401
        return view(**kwargs)

# TODO(2)(3)
    if user is None:
        return jsonify(error="Incorrect username."), 400
    if not check_password_hash(user.password, password):
        return jsonify(error="Incorrect password."), 400

# TODO(4)
@bp.post("/logout")
def logout():
    session.clear()
    return "", 204

# TODO(5)
@bp.get("/me")
def me():
    if g.user is None:
        return jsonify(user=None)
    return jsonify(id=g.user.id, username=g.user.username)
```
</details>

---

## 🧠 解説

**Blueprint = 機能ごとのルート束**
```python
bp = Blueprint("auth", __name__, url_prefix="/auth")
```
`auth` に属するルートは全部 `/auth/...` になります（`/auth/register` など）。
機能ごとにファイルを分けられ、ファクトリで `register_blueprint` した時に初めてアプリに合流します。

> 🔗 **React との接続**: Blueprint は React Router の「機能単位でまとめた `<Route>` グループ」に近い発想。関連するルートを1ファイルに凝集させ、あとで束ねて登録します。

**セッション Cookie 認証の3点セット**
1. **保存**: ログイン成功時に `session["user_id"] = user.id`。Flask は中身を `SECRET_KEY` で**署名**した Cookie にしてブラウザへ返す（改ざん不可）
2. **復元**: `@bp.before_app_request` の `load_logged_in_user` が**毎リクエストの前**に走り、Cookie の `user_id` から `g.user` を復元する
3. **保護**: `login_required` が `g.user is None` を見て未ログインを弾く

`session.clear()` をログイン時に入れているのは、以前のセッション残骸を消して**セッション固定攻撃**を防ぐため。

> 🔗 **Django との接続**: `g` は「リクエストの間だけ生きる入れ物」。Django の `request.user` を `before_app_request` で毎回セットしているイメージです。

**`request.get_json(silent=True) or {}`**
🔁 置き換えの要。元記事の `request.form['username']`（HTML フォーム）を、`request.get_json()`（JSON ボディ）に変えています。`silent=True` はボディが JSON でない/空でも例外を投げず `None` を返す設定で、`or {}` と合わせて安全に `.get()` できます。

**パスワードは必ずハッシュで**
`generate_password_hash(password)` で保存、`check_password_hash(stored, input)` で照合。平文保存は厳禁。これは元記事と完全に同じ（Werkzeug の関数をそのまま使用）。

---

## 🔮 予測 → 動作確認

**実行前に予想してみよう。**
- `register` に既存ユーザー名を送ったら、ステータスは？ ボディは？
- `login` 成功のレスポンスに付く `Set-Cookie` は何のため？

サーバを起動（別ターミナルで。MySQL が `healthy` であること）:
```bash
uv run flask --app flaskr run --debug
```

動作確認（`-c cookie.txt` で Cookie を保存し、ログイン状態を引き継ぐ）:
```bash
# 1) 登録
curl -s -X POST http://127.0.0.1:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# 2) 同じ名前で再登録（重複エラーを予想して）
curl -s -X POST http://127.0.0.1:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# 3) ログイン（Cookie を cookie.txt に保存）
curl -s -c cookie.txt -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# 4) 保存した Cookie を送って現在のユーザーを確認
curl -s -b cookie.txt http://127.0.0.1:5000/auth/me
```

期待される出力（順に）:
```json
{"id":1,"username":"test"}
{"error":"User test is already registered."}
{"id":1,"username":"test"}
{"id":1,"username":"test"}
```
- 2) は重複なので **400** + エラー JSON
- 3) のレスポンスヘッダに `Set-Cookie: session=...` が付く。これがログイン状態の証
- 4) は Cookie を送っているので `g.user` が復元され、自分の情報が返る（Cookie を付けないと `{"user": null}`）

> 💡補足: `curl -i` を付けるとヘッダも見えます。3) で `Set-Cookie` が、4) の `-b` が効いているのを確認できます。

---

## ✅ 想起チェック

**見ないで説明してみよう:** ログインしてから `/auth/me` が自分を返すまで、Cookie・`session`・`g.user`・`before_app_request` がどう連携するか、順を追って説明できますか？

<details><summary>解答例</summary>

1. `login` 成功時に `session["user_id"]=id` → Flask が `SECRET_KEY` で署名した Cookie を返す。
2. ブラウザ（curl）は以降のリクエストにその Cookie を自動で付ける。
3. 毎リクエストの前に `load_logged_in_user`(`@before_app_request`) が走り、Cookie 内の `user_id` から DB を引いて `g.user` にセット。
4. `/auth/me` は `g.user` を見て自分の情報を返す。`g` はそのリクエストの間だけ有効な入れ物。
</details>

**小問:** 元記事の `redirect(url_for("index"))` と `flash(error)` は、REST API 化でそれぞれ何に置き換わった？

<details><summary>解答例</summary>

- `redirect(url_for("index"))` → **JSON レスポンス + ステータスコード**（例: 登録成功は `201` でユーザー情報を返す）。ページ遷移はフロント（React）側が判断して行う。
- `flash(error)` → **`jsonify(error=...) ` + 4xx ステータス**。画面へのメッセージ表示はフロントがそのエラー文字列を受け取って行う。
</details>

---

次は [Step 4: 記事 CRUD API](./04-blog-api.md)。ここから提示量が減り、自力実装が中心になります。
