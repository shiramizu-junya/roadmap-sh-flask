# Step 3: 認証 API（Blueprint / パスワードハッシュ / セッション Cookie）

← [Step 2](./02-database-sqlalchemy.md) ／ [目次](./README.md) ／ 次: [Step 4](./04-blog-api.md)

**作るもの**: `POST /auth/register` `POST /auth/login` `POST /auth/logout` `GET /auth/me` の4本を、**Blueprint** に分けて実装する
**重要度**: 🔴 **毎日書く**（認証はほぼ全アプリで書く。Blueprint 分割は実務Flaskの標準）
**前ステップとの接続**: Step 2 の `User` モデルに、登録・ログインのロジックを乗せる。ルートは `create_app` 直書きをやめて Blueprint に移す

> 🔁 **置き換え**: 公式は `flash()` で画面にメッセージ、`redirect` で画面遷移する。
> この教材は **JSON のエラーボディ + HTTP ステータス**（`401`/`409` 等）を返し、ログイン状態は**セッション Cookie** で保つ。

> ⏭️ **後で回収（Step 1 の宣言）**: Step 1 で「Blueprint は Step 3 で導入する」と予告した。ここで回収する。

---

## 3-1. Blueprint とは（先に概念）

`create_app` にルートを全部直書きすると、機能が増えたとき1ファイルが膨張します。
**Blueprint（ブループリント）** は「関連するルートを1つの束にまとめる部品」です。`auth` の束、`posts` の束、と分けて、最後に `create_app` で**登録**します。

> 🧠 **考え方**: 「機能ごとにルートを束ね、アプリに後付けする」。React でいう「機能ごとにコンポーネント/ルーターを分けて、ルート集約点で束ねる」と同じ発想。

```
flaskr-api/flaskr/
├─ __init__.py     ← create_app。Blueprint を「登録」する
├─ models.py       ← Step 2
└─ auth.py         ← ★新規。auth Blueprint（登録/ログイン等）
```

---

## 3-2. パスワードは平文で保存しない（先に前提）

パスワードをそのままDBに入れるのは重大な事故のもとです。**ハッシュ化**して保存し、照合はハッシュ同士で行います。
Flask に同梱の `werkzeug` にハッシュ関数があるので、それを使います（追加インストール不要）。

| 関数 | 役割 |
|---|---|
| `generate_password_hash(平文)` | 平文 → 保存用ハッシュ文字列 |
| `check_password_hash(ハッシュ, 平文)` | 照合。合っていれば `True` |

---

## 3-3. auth Blueprint を書く（コード全文・写経）

**ファイル: `flaskr-api/flaskr/auth.py`（全文）**

```python
import functools

from flask import Blueprint, g, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .models import User, db

# "auth" という名前の Blueprint。URLは全部 /auth から始める
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user():
    """毎リクエストの前に、セッションの user_id から User を復元して g.user に置く。"""
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id is not None else None


def login_required(view):
    """ログイン必須のルートに付けるデコレータ。未ログインなら 401 を返す。"""
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return {"error": "authentication required"}, 401
        return view(*args, **kwargs)

    return wrapped_view


def user_to_dict(user):
    """User を JSON にできる辞書へ変換する。"""
    return {"id": user.id, "username": user.username}


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return {"error": "username and password are required"}, 400

    exists = db.session.scalar(
        db.select(User).filter_by(username=username)
    )
    if exists is not None:
        return {"error": "username already taken"}, 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    return user_to_dict(user), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    user = db.session.scalar(
        db.select(User).filter_by(username=username)
    )
    if user is None or not check_password_hash(user.password_hash, password or ""):
        return {"error": "invalid credentials"}, 401

    session.clear()
    session["user_id"] = user.id
    return user_to_dict(user), 200


@bp.post("/logout")
def logout():
    session.clear()
    return "", 204


@bp.get("/me")
def me():
    if g.user is None:
        return {"user": None}, 200
    return {"user": user_to_dict(g.user)}, 200
```

---

## 3-4. 🔬 構文解剖

### 🔬 構文解剖: `import functools`

| 部品 | 意味 |
|---|---|
| `import functools` | 標準ライブラリ `functools` を丸ごと取り込む。以降 `functools.wraps` と使う |

`from ... import ...`（名前を取り出す）と違い、`import functools` は**モジュール名経由で使う**形。両方 Python の import。

### 🔬 構文解剖: `Blueprint("auth", __name__, url_prefix="/auth")`

| 部品 | 意味 |
|---|---|
| `Blueprint(...)` | Blueprint インスタンスを作る |
| `"auth"` | Blueprint の名前（内部識別子。URL生成などで使う） |
| `__name__` | Step 1 と同じ。この Blueprint の位置の基準 |
| `url_prefix="/auth"` | **この束のルート全部の頭に `/auth` を付ける**。`@bp.post("/login")` は実際 `POST /auth/login` になる |
| `bp = ...` | 慣習的に Blueprint 変数は `bp` と名付ける |

**既知スタックとの対応**: Express の `Router()` + `app.use("/auth", router)` の「prefix 付きルーター」に相当。

### 🔬 構文解剖: `@bp.before_app_request`

| 部品 | 意味 |
|---|---|
| `@bp.before_app_request` | デコレータ。**毎リクエストの処理前**に、下の関数を必ず実行する |
| `before_app_request` | `app` 全体に効く（`before_request` は自 Blueprint 限定。`app` を付けると全体） |

**役割**: ルート本体が動く前に「今ログインしているのは誰か」を毎回セットしておく。
**既知スタックとの対応**: Express のミドルウェア（`app.use((req,res,next)=>{...})`）で `req.user` を毎回詰めるのと同じ。

### 🔬 構文解剖: `session.get("user_id")` と `g.user`

| 部品 | 意味 |
|---|---|
| `session` | Flask の**セッション**。中身は暗号署名された Cookie に保存される（Step 1 の `SECRET_KEY` で署名） |
| `session.get("user_id")` | 辞書の `.get(キー)`。キーが無ければ例外ではなく `None` を返す安全な取り出し |
| `g` | **リクエスト1回きりの一時置き場**（global の g だが「今のリクエスト内だけ」有効） |
| `g.user = ...` | 今回のリクエスト中、どこからでも `g.user` で現在ユーザーを参照できるようにする |

**`session` と `g` の違い**: `session` は**Cookie に残りリクエストをまたいで続く**（ログイン状態）。`g` は**そのリクエストが終わると消える**（毎回作り直す作業用メモ）。
**既知スタックとの対応**: `session` はサーバーが署名した Cookie ベースのセッション（`express-session` 相当）。`g` は `res.locals` / リクエストスコープの入れ物。
**なぜ `user_id` だけ session に入れるか**: Cookie は小さく保ちたい & 改ざん対策。IDだけ保存し、ユーザー本体は毎回 `g.user` にDBから復元する。

### 🔬 構文解剖: `db.session.get(User, user_id)`

| 部品 | 意味 |
|---|---|
| `db.session` | SQLAlchemy の**セッション**（DBとのやり取りの窓口。上の Flask の session とは別物） |
| `.get(User, user_id)` | **主キー**で1件取得。見つからなければ `None` |

> ⚠️ **紛らわしさ注意**: `session`（Flask のログイン用Cookie）と `db.session`（DB操作の窓口）は**別物**。同じ「session」でも役割が違う。

### 🔬 構文解剖: 三項演算子 `A if 条件 else B`

```python
g.user = db.session.get(User, user_id) if user_id is not None else None
```

| 部品 | 読み方 | 意味 |
|---|---|---|
| `A if 条件 else B` | — | Python の**条件式**。条件が真なら `A`、偽なら `B`。JS の `条件 ? A : B` に相当 |
| `is not None` | イズノットノン | **`is` は同一性の比較**。`None`（JS の null 相当）かどうかは `==` でなく `is` で見るのが Python の作法 |

**なぜ `is None` か（`== None` でない）**: `None` は唯一の特別な値なので、値の等価(`==`)ではなく同一性(`is`)で判定するのが正しく・速い。慣用。

### 🔬 構文解剖: `login_required` デコレータの自作

```python
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return {"error": "authentication required"}, 401
        return view(*args, **kwargs)
    return wrapped_view
```

| 部品 | 読み方 | 意味 |
|---|---|---|
| `def login_required(view):` | — | **関数を受け取る関数**。`view` は元のルート関数 |
| 内側の `def wrapped_view` | — | 元関数を包む新しい関数を中で定義する（**クロージャ**） |
| `@functools.wraps(view)` | ラップス | 包むとき、元関数の名前やdocstringを引き継ぐ。付けないとデバッグ時に名前が消える |
| `*args` | アスターアーグス | 可変長の**位置引数**をまとめて受ける記号。`*` は「残り全部を集める」 |
| `**kwargs` | ダブルアスターquargs | 可変長の**キーワード引数**をまとめて受ける。`**` は「名前付き残り全部」 |
| `return view(*args, **kwargs)` | — | 集めた引数を**そのまま展開して**元関数に渡す（`*`/`**` で展開） |

**デコレータの正体**: `@login_required` を関数の上に貼ると、その関数が `login_required(その関数)` に置き換わる。
つまり「ログインチェックを先にやって、OKなら元の処理へ」という**ラップ**を1行で足せる。Step 1 の `@app.get` と同じ「関数を加工する」仕組みを、今回は**自分で書いた**。
**`*args, **kwargs` の意味**: どんな引数のルートでも包めるように「引数を全部そのまま受けて、そのまま渡す」定型。ルートが `<id>` を取っても取らなくても対応できる。
**既知スタックとの対応**: Express の認証ミドルウェア `requireAuth` を、関数を包む高階関数として書いたもの。React の HOC(`withAuth(Component)`)とも同じ構造。

### 🔬 構文解剖: `request.get_json(silent=True) or {}`

| 部品 | 意味 |
|---|---|
| `request.get_json()` | リクエストボディを JSON として解釈し辞書で返す |
| `silent=True` | ボディが JSON でない/空でも**例外を投げず `None`** を返す |
| `... or {}` | `None`（偽）なら右の空辞書 `{}` を使う。**Python の `or` は「左が偽なら右」を返す**（真偽だけでなく値を返す） |

**`data.get("username")`**: 辞書の `.get` はキーが無ければ `None`。`data["username"]` だと無いとき例外になるので、入力検証前は `.get` が安全。
**既知スタックとの対応**: `req.body?.username ?? undefined` のような防御的取り出し。`X or Y` は JS の `X || Y` に相当（値を返す点も同じ）。

### 🔬 構文解剖: 戻り値 `辞書, ステータス` のタプル

```python
return {"error": "..."}, 400
```

| 部品 | 読み方 | 意味 |
|---|---|---|
| `A, B` | — | カンマで並べると**タプル**（不変の組）になる。ここでは `(本体, ステータスコード)` |
| Flask の仕様 | — | ハンドラが `(本体, ステータス)` を返すと、本体を JSON 化し**そのステータスで**返す |

**既知スタックとの対応**: `res.status(400).json({error:...})` を、`return (本体, 400)` の1行で表す。
**なぜタプルか**: Python は複数値をカンマで束ねられる（`return a, b`）。Flask はこの慣習に乗って `(body, status)` を受ける。

### 🔬 構文解剖: `User(username=..., password_hash=...)` と `db.session.add / commit`

| 部品 | 意味 |
|---|---|
| `User(username=..., ...)` | モデルのインスタンス生成＝**新しい行(未保存)** を作る。キーワード引数で各列を指定 |
| `db.session.add(user)` | セッションに「この行を追加予定」と登録（まだDBには書かれない） |
| `db.session.commit()` | ここで**まとめてDBに書き込む**（トランザクション確定）。`user.id` もここで採番される |

**なぜ add と commit が分かれるか**: 複数の変更をためて `commit` で一括確定できる（途中で失敗したら全部取り消せる＝トランザクション）。
**既知スタックとの対応**: `session.add` は「ステージング(git add に近い)」、`commit` は確定。Prisma の即時 `create` と違い、SQLAlchemy は明示 commit 方式。

### 🔬 構文解剖: `db.session.scalar(db.select(User).filter_by(username=username))`

| 部品 | 意味 |
|---|---|
| `db.select(User)` | 「`User` を検索する」クエリを組み立てる（まだ実行しない） |
| `.filter_by(username=username)` | WHERE 条件。`username` 列が一致する行に絞る |
| `db.session.scalar(...)` | クエリを実行し**1件（スカラー値）**を返す。無ければ `None` |

**既知スタックとの対応**: Prisma の `findFirst({ where: { username } })`。`select(...).filter_by(...)` は SQL の `SELECT ... WHERE ...` をメソッドで組み立てている。
**なぜ `scalar` か**: 「0か1件」を取りたいとき。複数取りたいときは `db.session.scalars(...).all()`（Step 4 で使う）。

> 💡 **補足**: 古い SQLAlchemy 記事は `User.query.filter_by(...).first()` と書く。
> 新しい書き方は `db.session.scalar(db.select(User).filter_by(...))`。この教材は新スタイルに統一する。

### 🔬 構文解剖: `return "", 204`（本文なしレスポンス）

| 部品 | 意味 |
|---|---|
| `""` | 空の本文 |
| `204` | HTTP `204 No Content`。「成功したが返す中身は無い」。logout やdelete で使う |

---

## 3-5. `create_app` に Blueprint を登録する（差分）

**ファイル: `flaskr-api/flaskr/__init__.py`（Step 2 からの差分反映・全文）**

```python
from flask import Flask
from flask_cors import CORS

from .models import db


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "dev"
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr"
    )

    db.init_app(app)

    # ★追加：React(:5173) から Cookie 付きで叩けるように CORS を許可
    CORS(
        app,
        resources={r"/*": {"origins": ["http://localhost:5173"]}},
        supports_credentials=True,
    )

    # ★追加：auth Blueprint を登録
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
```

先に CORS ライブラリを入れます:

```bash
uv add flask-cors
```

### 🔬 構文解剖: CORS 設定

| 部品 | 意味 |
|---|---|
| `CORS(app, ...)` | 別オリジン(React:5173)からのブラウザリクエストを許可する設定 |
| `resources={r"/*": {...}}` | どのパスに適用するか。`r"/*"` は「全パス」。`r"..."` は**raw文字列**（後述） |
| `origins=[...]` | 許可する送信元。React の開発サーバー `http://localhost:5173` |
| `supports_credentials=True` | **Cookie を伴うリクエストを許可**。セッションCookieを使うので必須 |

**`r"/*"` の `r` とは**: **raw文字列**。バックスラッシュを特殊文字として解釈しない文字列リテラル。正規表現やパスで使う。ここでは実害はないが正規表現的パターンなので慣習で `r` を付ける。
**なぜ CORS が要るか**: ブラウザは「別オリジンへのリクエスト」を既定でブロックする。フロント(5173)とAPI(5000)がポート違い＝別オリジンなので、サーバー側で明示許可する。詳細は Step 6。

> ⏭️ **後で回収**: `supports_credentials` とフロント側 `fetch(credentials:"include")` の対応関係は **Step 6** で図解する。今は「Cookie を使うから True」でよい。

### 🔬 構文解剖: `from .auth import bp as auth_bp`（関数内 import と別名）

| 部品 | 意味 |
|---|---|
| `from .auth import bp` | 同パッケージの `auth.py` から `bp` を取り込む |
| `as auth_bp` | **別名を付ける**。`bp` のままだと他 Blueprint と名前衝突するので分かりやすく改名 |
| 関数の**中**で import | 循環インポート回避のため、`create_app` 内で遅延 import する定番テク |
| `app.register_blueprint(auth_bp)` | Blueprint をアプリに登録。これで `/auth/*` が有効になる |

---

## 3-6. 🏢 実務メモ / ⚠️ アンチパターン

### 🏢 実務メモ
`user_to_dict` のような**シリアライズ（モデル→JSON辞書）を関数に切り出す**のは実務の基本。
`password_hash` を絶対にレスポンスへ含めないため、「返してよい列だけ」を明示的に組み立てる。モデルをそのまま返すと機密が漏れる。

### ⚠️ やりがち
> **やりがち**: ログイン成功時に `session["user_id"]` を入れる前に `session.clear()` を忘れ、前ユーザーの残骸が混ざる。
> **現場では**: ログイン時は必ず `session.clear()` してから新しい `user_id` を入れる（セッション固定化攻撃対策にもなる）。

---

## 3-7. 🔮 予測 → 動作確認

前提: MySQL 起動済み・テーブル作成済み（`docker compose up -d` → `uv run flask --app flaskr init-db`）。

### サーバー起動

```bash
uv run flask --app flaskr run --port 5000
```

### 🔮 実行前に予想しよう
1. 同じ username で2回 `register` すると、2回目のステータスは？
2. `login` 成功のレスポンスヘッダに現れる、状態を保つための仕組みは何？
3. ログインせずに `/auth/me` を叩くと、ボディは何が返る？

### 動作確認（別ターミナル）

```bash
# 1) 登録
curl -i -X POST http://127.0.0.1:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pw12345"}'

# 2) 同じ名前でもう一度 → 409 になるはず
curl -i -X POST http://127.0.0.1:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pw12345"}'

# 3) ログイン（Cookie をファイルに保存: -c）
curl -i -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pw12345"}' \
  -c cookie.txt

# 4) 保存した Cookie を送って /auth/me（-b）
curl -i http://127.0.0.1:5000/auth/me -b cookie.txt
```

### 🔬 構文解剖: curl のオプション

| 部品 | 意味 |
|---|---|
| `-X POST` | HTTP メソッドを指定 |
| `-H "Content-Type: application/json"` | ヘッダ追加。JSON を送ると伝える |
| `-d '{...}'` | 送信ボディ（data） |
| `-c cookie.txt` | レスポンスの Set-Cookie を**ファイルに保存**（cookie jar） |
| `-b cookie.txt` | 保存した Cookie を**送信**する |

### 期待される出力（要点）
- 1) `201 Created` + `{"id":1,"username":"alice"}`
- 2) `409 Conflict` + `{"error":"username already taken"}`（予想1）
- 3) `200 OK` + レスポンスに `Set-Cookie: session=...`（予想2＝セッションCookie）
- 4) `200 OK` + `{"user":{"id":1,"username":"alice"}}`。Cookie 無しなら `{"user":null}`（予想3）

---

## 3-8. ✅ 想起チェック

<details><summary>Q1. `session` と `g` の違いは？</summary>

`session` は暗号署名Cookieに保存されリクエストをまたいで続く（ログイン状態）。`g` はそのリクエスト内だけ有効な作業用の入れ物で、毎リクエスト作り直す。
</details>

<details><summary>Q2. `session` と `db.session` は同じもの？</summary>

別物。`session` は Flask のログイン用Cookieセッション、`db.session` は SQLAlchemy のDB操作の窓口。名前が同じだけ。
</details>

<details><summary>Q3. `@login_required` を貼ると何が起きる？ `*args, **kwargs` は何のため？</summary>

関数が「ログインチェック→OKなら元処理」に包まれる。`*args/**kwargs` は、どんな引数のルートでも包めるよう引数を全部そのまま受け取って渡すための記法。
</details>

<details><summary>Q4. なぜ `db.session.add` と `db.session.commit` が分かれている？</summary>

複数の変更をためて `commit` で一括確定でき、途中失敗時に全部取り消せる（トランザクション）ため。
</details>

---

## ✍️ ブランクページ（章末の再現）

`auth.py` を閉じて、白紙から次を再現:

- `bp = Blueprint("auth", __name__, url_prefix="/auth")`
- `before_app_request` で `g.user` を復元
- `login_required` デコレータ（`functools.wraps` / `*args, **kwargs`）
- `register`（409 と 400 の分岐、ハッシュ化、`add`→`commit`、201）
- `login`（照合、`session.clear()`→`session["user_id"]`）
- `logout`（`session.clear()`→204）／`me`

思い出せなかった行の 🔬 構文解剖（3-4）だけ読み返す。

---

## まとめ

- **Blueprint** でルートを機能ごとに束ね、`register_blueprint` で登録する
- パスワードは `generate_password_hash` で保存、`check_password_hash` で照合
- ログイン状態は `session["user_id"]`（署名Cookie）、現在ユーザーは毎回 `g.user` に復元
- `@login_required` を**自作デコレータ**として実装した
- 別オリジンの React 用に **CORS + `supports_credentials`** を許可した

次の [Step 4](./04-blog-api.md) で、この認証を使って**記事の CRUD API（本人のみ編集可）**を作ります。
