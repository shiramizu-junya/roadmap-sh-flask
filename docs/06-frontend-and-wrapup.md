# Step 6: React 連携・つまずき・まとめ・宿題・発展

← [Step 5](./05-testing.md) ／ [目次](./README.md)

このステップは、元記事の **Templates / Static Files / Deploy** に相当する部分を、REST API 版として扱います。
🔁 **置き換え**: 元記事は Jinja テンプレート + CSS で画面を作りましたが、ここでは **React が API を叩いて画面を描く**構成にします。

---

## 6-1. React から API を叩く（Templates/Static の置き換え）

> **これは補足寄り。** 教材の核は Flask 側。React 側は「Cookie 付き fetch で JSON をやり取りする」型だけ押さえれば十分です。

`frontend/src/api.ts` を新規作成:

```ts
// すべてのリクエストで Cookie を送る(credentials:"include")のが最重要ポイント。
// これが無いと、ログインしても session Cookie が送られず 401 になる。
const BASE = "http://localhost:5000";

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    credentials: "include", // ← セッション Cookie を送受信する
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
  });
  const data = res.status === 204 ? null : await res.json();
  if (!res.ok) throw new Error(data?.error ?? "Request failed");
  return data;
}

export type Post = {
  id: number; title: string; body: string;
  created: string; author_id: number; username: string;
};

export const api = {
  login: (username: string, password: string) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request("/auth/me"),
  listPosts: (): Promise<Post[]> => request("/posts"),
  createPost: (title: string, body: string): Promise<Post> =>
    request("/posts", { method: "POST", body: JSON.stringify({ title, body }) }),
};
```

`frontend/src/App.tsx` を差し替え（最小の一覧 + 作成）:

```tsx
import { useEffect, useState } from "react";
import { api, type Post } from "./api";

export default function App() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [title, setTitle] = useState("");

  // 初回に一覧を取得（React の useEffect = 元記事の index ビューが描画時にやっていたこと）
  useEffect(() => { api.listPosts().then(setPosts); }, []);

  async function handleCreate() {
    await api.login("test", "test");        // デモ用に固定ログイン
    await api.createPost(title, "body...");
    setPosts(await api.listPosts());        // 作成後に再取得
    setTitle("");
  }

  return (
    <div>
      <h1>Flaskr Posts</h1>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="title" />
      <button onClick={handleCreate}>Create</button>
      <ul>
        {posts.map((p) => (
          <li key={p.id}><b>{p.title}</b> by {p.username}</li>
        ))}
      </ul>
    </div>
  );
}
```

**🔮 予測 → 動作確認:** MySQL（`docker compose up -d`）・Flask（`uv run flask --app flaskr run --debug`）・React（`npm run dev`）を起動し、`http://localhost:5173` を開く。
「実行前に予想してみよう」: `credentials:"include"` を**消したら**どうなる？（→ ログインしても Cookie が送られず、作成が 401 で失敗する）

> 🔗 **接続**: `useEffect(() => api.listPosts()...)` は、元記事の `index` ビューが「アクセス時に全記事を SELECT して埋め込む」処理を、クライアント側に移したもの。データ取得のタイミングがサーバ→クライアントに移っただけで、やっていることは同じです。

---

## 6-2. 本番デプロイの要点：Flask も Docker に入れる（補足）

> **補足。** 元記事の Deploy 章に相当。ここでは学習構成（MySQLだけ Docker）から一歩進めて、**Flask アプリも Docker イメージにして、MySQL と一緒に compose で丸ごと起動**する「フルコンテナ化」を紹介します。本番/CI に近い形です。

### ① 本番サーバ用に gunicorn を追加

```bash
uv add gunicorn        # 開発サーバ(flask run)は本番非対応。WSGIサーバを使う
```

### ② Flask アプリを箱に詰める `Dockerfile`

`flaskr-api/Dockerfile` を作成:
```dockerfile
# ベースは軽量な Python イメージ
FROM python:3.12-slim

# uv 本体を公式イメージからコピー（イメージ内でも uv を使う）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先に依存定義だけコピーして入れる（キャッシュが効いてビルドが速くなる）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev          # uv.lock どおりに再現（本番なので --no-dev）

# アプリ本体をコピー
COPY . .

# gunicorn でファクトリを起動（4ワーカー、5000番で待受）
CMD ["uv", "run", "gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "flaskr:create_app()"]
```

### ③ アプリと DB をまとめて起動する compose

`docker-compose.prod.yml`（例）:
```yaml
services:
  db:                       # Step0 の db サービスと同じ（MySQL）
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: flaskr
      MYSQL_USER: flaskr
      MYSQL_PASSWORD: flaskr
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uflaskr", "-pflaskr"]
      interval: 5s
      timeout: 3s
      retries: 20

  web:                      # ② の Dockerfile からビルドする Flask アプリ
    build: .
    ports:
      - "5000:5000"
    environment:
      # ホスト名は localhost ではなく「サービス名 db」になる点に注意（後述）
      DATABASE_URL: mysql+pymysql://flaskr:flaskr@db:3306/flaskr?charset=utf8mb4
      SECRET_KEY: ${SECRET_KEY}    # 本番の秘密鍵は環境変数で注入
    depends_on:
      db:
        condition: service_healthy  # DBが healthy になるまで web を待たせる

volumes:
  mysql_data:
```

起動:
```bash
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex())") \
  docker compose -f docker-compose.prod.yml up --build -d
# 初回はテーブル作成
docker compose -f docker-compose.prod.yml exec web uv run flask --app flaskr init-db
```

**重要ポイント（丁寧に）:**
- 🔑 **接続先ホストが `localhost` → `db` に変わる**: コンテナ同士は compose の**サービス名**で通信します。Flask もコンテナ内にいるので、MySQL を `localhost` ではなく **`db`（サービス名）** で呼びます。学習構成（Flask がPC上）では `localhost` だったのが、フルコンテナ化では `db` になる——ここが混乱しやすい最重要ポイントです
- 🔑 **`SECRET_KEY` は本番用に差し替える**: `dev` のままは危険。`secrets.token_hex()` で生成し、環境変数で注入（コードにもGitにも置かない）
- 🔑 **`depends_on` + `condition: service_healthy`**: MySQL の起動完了を待ってから web を立ち上げる（起動順の事故を防ぐ）
- **DB の差し替え**: 将来 PostgreSQL 等にしても `DATABASE_URL` を変えるだけでコードはほぼそのまま（ORM の恩恵）
- **CORS の `origins`**: 本番はフロントの実ドメインに変更する

---

## 6-3. つまずきポイント（よくあるエラーと対処）

**Docker / MySQL / uv 系**

| 症状 | 原因 | 対処 |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop 未起動 | Docker Desktop アプリを起動（🐳 が Running）。CLI だけでは動かない |
| `Can't connect to MySQL server` / `Connection refused` (2003) | MySQL がまだ起動途中 / 未起動 | `docker compose ps` で `healthy` を待つ。未起動なら `docker compose up -d` |
| `Access denied for user 'flaskr'` | `.env` の user/pass が compose と不一致 | `DATABASE_URL` の `flaskr:flaskr` と compose の `MYSQL_USER/PASSWORD` を一致させる |
| `Unknown database 'flaskr_test'` | テスト用DBが未作成 | `docker/initdb/01-init.sql` を用意して `docker compose down -v && up -d`（initスクリプトは初回のみ実行） |
| `RuntimeError: 'cryptography' package is required` | MySQL8 の認証に必要なライブラリ不足 | `uv add cryptography`（本教材は追加済み） |
| `Bind for 0.0.0.0:3306 failed: port is already allocated` | PCの3306が使用中（既存MySQL等） | compose の `ports` を `"3307:3306"` に変え、`.env` の接続先も `localhost:3307` に |
| `VARCHAR requires a length on dialect mysql` | `db.String` に長さ未指定 | `db.String(80)` のように**長さを付ける**（MySQL 必須。[Step2](./02-database-sqlalchemy.md)参照） |
| `sqlalchemy ... doesn't exist` (テーブル無し) | `init-db` 忘れ | `uv run flask --app flaskr init-db`。テストは `create_all()` がフィクスチャにあるか確認 |
| `command not found: flask` | `uv run` を付け忘れ | `uv run flask ...` の形で実行する |

**アプリ / API 系**

| 症状 | 原因 | 対処 |
|---|---|---|
| React から呼ぶと CORS エラー | `Flask-Cors` 未設定 / `origins` 不一致 | `CORS(app, resources=..., supports_credentials=True)`。`origins` を `http://localhost:5173` に一致させる |
| ログインしたのに毎回 401 | Cookie が送られていない | fetch に `credentials:"include"`、Flask 側 `supports_credentials=True`。`origins` に `*` は使えない（credentials 時は具体的オリジン必須） |
| `415 Unsupported Media Type` | `Content-Type: application/json` が無い | ヘッダを付ける。または `request.get_json(silent=True)` で寛容に受ける（本教材は後者を採用済み） |
| `RuntimeError: Working outside of application context` | `app_context` 無しで DB 操作 | スクリプトやシェルでは `with app.app_context():` の中で `db.session` を使う |
| `flask --app flaskr` で `Could not import` | 実行ディレクトリ違い | `flaskr/` の**親**（`flaskr-api/`）で実行する |
| フルコンテナ化で web が DB に繋がらない | 接続先を `localhost` にしている | コンテナ間はサービス名で通信。`DATABASE_URL` のホストを `db` にする（[6-2](#6-2-本番デプロイの要点flask-も-docker-に入れる補足)参照） |
| 登録が常に成功してしまう/重複を弾けない | `username` の `unique=True` 未設定、または重複チェック漏れ | モデルの制約と `filter_by(...).first()` チェックの両方を確認 |

---

## 6-4. まとめ（学んだことの要点）

- **アプリケーションファクトリ**: 設定・DB・Blueprint の登録を `create_app()` に集約。テスト設定を注入できる
- **Blueprint**: 機能ごと（`auth`/`blog`）にルートを分割し、ファクトリで合流
- **SQLAlchemy**: モデルクラス＝テーブル。`to_dict()` で JSON 化。`close_db` は自動化され不要
- **セッション Cookie 認証**: `session["user_id"]` に保存 →`before_app_request` で `g.user` 復元 → `login_required` で保護
- **REST 設計**: リソースは URL（`/posts/<id>`）、操作は HTTP メソッド。結果は JSON + ステータスコード
- **認可の一元化**: `get_post` で 404/403 をまとめ、各ビューは1行呼ぶだけ
- **テスト**: MySQL テスト用DB(`flaskr_test`)を `drop_all`/`create_all` で初期化するフィクスチャ + テストクライアントで、正常系と 401/403/404 の分岐を網羅
- **環境（今回追加した実務スタック）**: **uv** で Python/依存を一括管理、**MySQL** を **Docker** で起動、`.env`（環境変数）で接続先を切り替え、本番は **gunicorn + フルコンテナ化**
- **MySQL の勘所**: `db.String` は**長さ必須**（`String(80)`）、コンテナ間通信は**サービス名**（`db`）で行う
- **置き換えの勘所**: `flash`→JSON エラー、`redirect`→ステータスコード、`render_template`→`to_dict`+React、`request.form`→`request.get_json`、`sqlite`→`MySQL`、`venv/pip`→`uv`

---

## 6-5. 宿題（アウトプット課題）

本編で作った `flaskr` の**続き**として解きます。Lv1 → Lv3 で難しくなります。
まず自力で書き、`curl` の判定基準を満たしてから折りたたみで照合してください。

### 🟢 Lv1-A（認証・基礎確認）: パスワード長のバリデーション

**課題**
- `POST /auth/register` で、`password` が **4文字未満**なら `400` と `{"error":"Password must be at least 4 characters."}` を返す
- 既存の「必須チェック」の後ろに1つ条件を足すだけ

**ヒント**: `auth.py` の `register` の、password 必須チェックの直後に `len(password) < 4` の分岐を足す。

**判定基準**
```bash
curl -s -X POST http://127.0.0.1:5000/auth/register \
  -H "Content-Type: application/json" -d '{"username":"bob","password":"ab"}'
# => {"error":"Password must be at least 4 characters."}  (400)
```

<details><summary>解答例</summary>

```python
    if not password:
        return jsonify(error="Password is required."), 400
    if len(password) < 4:                                   # ← 追加
        return jsonify(error="Password must be at least 4 characters."), 400
```
</details>

### 🟢 Lv1-B（記事・基礎確認）: 一覧の件数制限

**課題**
- `GET /posts?limit=N` で先頭 N 件だけ返す。`limit` 未指定なら全件（本編どおり）

**ヒント**: `request.args.get("limit", type=int)` でクエリを取得。`None` でなければ `.limit(n)` を付ける。

**判定基準**
```bash
# 記事が2件以上ある状態で
curl -s "http://127.0.0.1:5000/posts?limit=1" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))"
# => 1
```

<details><summary>解答例</summary>

```python
from flask import request  # 既に import 済み

@bp.get("")
def index():
    query = Post.query.order_by(Post.created.desc())
    limit = request.args.get("limit", type=int)
    if limit is not None:
        query = query.limit(limit)
    return jsonify([p.to_dict() for p in query.all()])
```
</details>

### 🟡 Lv2-A（認証・応用）: パスワード変更 API

**課題**
- `PUT /auth/password`（**ログイン必須**）を追加
- ボディ `{"old_password":..., "new_password":...}`
- `old_password` が現在のと不一致なら `400 {"error":"Incorrect password."}`
- `new_password` が4文字未満なら `400`（Lv1-A と同基準）
- 成功時は `204`
- 変更後、新パスワードでログインできること

**ヒント**: `login_required` を使う。`check_password_hash(g.user.password, old_password)` で照合し、`g.user.password = generate_password_hash(new_password)` → `db.session.commit()`。

**判定基準**
```bash
# test でログイン済み(cookie.txt)として
curl -s -b cookie.txt -X PUT http://127.0.0.1:5000/auth/password \
  -H "Content-Type: application/json" \
  -d '{"old_password":"test","new_password":"newpass"}' -o /dev/null -w "%{http_code}\n"
# => 204
# 続けて新パスワードでログインできる
curl -s -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" -d '{"username":"test","password":"newpass"}' \
  -o /dev/null -w "%{http_code}\n"
# => 200
```

<details><summary>解答例</summary>

```python
@bp.put("/password")
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    old = data.get("old_password", "")
    new = data.get("new_password", "")

    if not check_password_hash(g.user.password, old):
        return jsonify(error="Incorrect password."), 400
    if len(new) < 4:
        return jsonify(error="Password must be at least 4 characters."), 400

    g.user.password = generate_password_hash(new)
    db.session.commit()
    return "", 204
```
</details>

### 🟡 Lv2-B（記事・応用）: キーワード検索

**課題**
- `GET /posts?q=キーワード` で、`title` **または** `body` に部分一致する記事だけ返す
- `q` 未指定なら全件（Lv1-B の `limit` と共存できるとなお良い）

**ヒント**: `from sqlalchemy import or_` を使い、`Post.title.ilike(f"%{q}%")` と `Post.body.ilike(...)` を `or_(...)` で結合し `.filter(...)`。

**判定基準**
```bash
# title に "first" を含む記事だけ返る
curl -s "http://127.0.0.1:5000/posts?q=first" | python3 -c "import sys,json;d=json.load(sys.stdin);print(all('first' in (p['title']+p['body']).lower() for p in d))"
# => True
```

<details><summary>解答例</summary>

```python
from sqlalchemy import or_

@bp.get("")
def index():
    query = Post.query.order_by(Post.created.desc())

    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Post.title.ilike(like), Post.body.ilike(like)))

    limit = request.args.get("limit", type=int)
    if limit is not None:
        query = query.limit(limit)

    return jsonify([p.to_dict() for p in query.all()])
```
</details>

### 🔴 Lv3（統合・発展）: コメント機能をフル実装

本編の知識（モデル・Blueprint・認証・認可・バリデーション・エラー処理・テスト）を**統合**する課題です。

**課題**
- `Comment` モデルを追加: `id` / `post_id`(FK→post) / `author_id`(FK→user) / `body` / `created`
- エンドポイント:
  - `GET /posts/<id>/comments` … その記事のコメント一覧（新しい順）。記事が無ければ **404**
  - `POST /posts/<id>/comments` … コメント投稿（**ログイン必須**）。`body` 空なら **400**。記事が無ければ **404**。成功時 **201** + 作成コメント
  - `DELETE /comments/<id>` … コメント削除（**ログイン必須 & コメント著者本人のみ**、他人は **403**、無ければ **404**）
- `Comment` に `to_dict()`（`username` 含む）
- **テストを最低3つ**書く: 投稿の正常系 / 未ログイン401 / 他人のコメント削除403

**ヒント（考え方のみ）**
- 記事の存在チェックは本編の `get_post(id, check_author=False)` を再利用できる
- コメント用にも `get_comment(id, check_author=True)` ヘルパーを作ると 404/403 を一元化できる（`get_post` と同じ設計）
- 新モデルを足したら **`uv run flask --app flaskr init-db` で作り直す**（`drop_all`+`create_all`）
- Blueprint は新設せず、`blog.py` に足してよい（ルートはコメント用に増やすだけ）

**判定基準**
```bash
# ログイン済み(cookie.txt)で、記事1にコメント投稿 → 201
curl -s -b cookie.txt -X POST http://127.0.0.1:5000/posts/1/comments \
  -H "Content-Type: application/json" -d '{"body":"nice post"}' -o /dev/null -w "%{http_code}\n"
# => 201

# 未ログインで投稿 → 401
curl -s -X POST http://127.0.0.1:5000/posts/1/comments \
  -H "Content-Type: application/json" -d '{"body":"x"}' -o /dev/null -w "%{http_code}\n"
# => 401

# 存在しない記事へ投稿 → 404
curl -s -b cookie.txt -X POST http://127.0.0.1:5000/posts/999/comments \
  -H "Content-Type: application/json" -d '{"body":"x"}' -o /dev/null -w "%{http_code}\n"
# => 404

# 一覧取得
curl -s http://127.0.0.1:5000/posts/1/comments
# => [{"id":1,"post_id":1,"author_id":1,"username":"test","body":"nice post","created":"..."}]
```
そして `pytest` が全て緑になること。

<details><summary>解答例（モデル・ビュー・テスト）</summary>

**flaskr/models.py に追記:**
```python
class Comment(db.Model):
    __tablename__ = "comment"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    author = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "author_id": self.author_id,
            "username": self.author.username,
            "body": self.body,
            "created": self.created.isoformat(),
        }
```

**flaskr/blog.py に追記:**
```python
from .models import db, Post, Comment  # import に Comment を追加


def get_comment(id, check_author=True):
    comment = db.session.get(Comment, id)
    if comment is None:
        abort(404, f"Comment id {id} doesn't exist.")
    if check_author and comment.author_id != g.user.id:
        abort(403)
    return comment


@bp.get("/<int:id>/comments")
def list_comments(id):
    get_post(id, check_author=False)          # 記事が無ければ 404
    comments = (Comment.query
                .filter_by(post_id=id)
                .order_by(Comment.created.desc())
                .all())
    return jsonify([c.to_dict() for c in comments])


@bp.post("/<int:id>/comments")
@login_required
def create_comment(id):
    get_post(id, check_author=False)          # 記事が無ければ 404
    data = request.get_json(silent=True) or {}
    body = data.get("body")
    if not body:
        return jsonify(error="Body is required."), 400

    comment = Comment(post_id=id, author_id=g.user.id, body=body)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


# コメント削除は /posts 配下でなく /comments/<id> にしたいので別 Blueprint 名前空間でもよいが、
# ここでは同 blueprint(url_prefix="/posts")の外に出すため add_url_rule を使わず、素直に別ルートにする:
@bp.delete("/comments/<int:id>")              # 実際の URL は /posts/comments/<id>
@login_required
def delete_comment(id):
    comment = get_comment(id)
    db.session.delete(comment)
    db.session.commit()
    return "", 204
```

> 補足: 上の `delete_comment` は `url_prefix="/posts"` の影響で URL が `/posts/comments/<id>` になります。判定基準どおり `/comments/<id>` にしたい場合は、`blog.py` 冒頭で
> `comments_bp = Blueprint("comments", __name__, url_prefix="/comments")` を別途作り、`delete_comment` をそちらに登録して、ファクトリで両方 `register_blueprint` してください。

**tests/test_comment.py:**
```python
from flaskr.models import db, Comment


def test_create_comment(client, auth, app):
    auth.login()
    res = client.post("/posts/1/comments", json={"body": "nice"})
    assert res.status_code == 201
    with app.app_context():
        assert Comment.query.count() == 1


def test_comment_login_required(client):
    res = client.post("/posts/1/comments", json={"body": "x"})
    assert res.status_code == 401


def test_delete_others_comment_forbidden(client, auth, app):
    # test がコメント投稿
    auth.login()
    cid = client.post("/posts/1/comments", json={"body": "mine"}).get_json()["id"]
    # 著者を other(id=2) に書き換え
    with app.app_context():
        c = db.session.get(Comment, cid)
        c.author_id = 2
        db.session.commit()
    # test は他人のコメントを消せない → 403
    assert client.delete(f"/posts/comments/{cid}").status_code == 403
```
</details>

---

## 6-6. 発展（次に学ぶとよいこと）

- **JWT / トークン認証**: セッション Cookie の代わりにトークンを使う SPA/モバイル向け認証。`Flask-JWT-Extended`
- **Marshmallow / Pydantic**: 入力バリデーションと `to_dict()` の自動化（スキーマ駆動）。手書きの検証を置き換えられる
- **Flask-Migrate（Alembic）**: モデル変更を `drop_all` せずマイグレーションで反映（本番の DB を壊さず更新）
- **ページネーション**: `Post.query.paginate(page, per_page)` で大量データに対応
- **Blueprint の分割拡大**: `api/v1` のようにバージョニング、`create_app` でのファクトリパターンの発展
- **本番運用**: `gunicorn`/`waitress` + リバースプロキシ、環境変数での設定管理、ロギング
- **フロント本格化**: React Router でルーティング、認証状態のグローバル管理（Context/Zustand）、フォームの `react-hook-form`

お疲れさまでした。上から順に進めたなら、元記事の全トピック（ファクトリ / DB / Blueprint / 認証 / CRUD / 認可 / テスト / デプロイ）を、実務スタックで再現できたはずです 🎉

← [目次に戻る](./README.md)
