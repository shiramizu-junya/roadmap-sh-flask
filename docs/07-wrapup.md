# Step 7: つまずき集 / まとめ / 宿題 / 発展

← [Step 6](./06-frontend.md) ／ [目次](./README.md)

**重要度**: 🟡 **読めればよい**（トラブル対処と定着課題。手元で詰まったとき参照する）

---

## 7-1. つまずきポイント（エラー全文 → 原因 → 対処）

### 環境（Docker / uv）

| エラー（抜粋） | 原因 | 対処 |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop 未起動 | クジラアイコンを起動してから再実行 |
| `Bind for 0.0.0.0:3306 failed: port is already allocated` | 3306 を別プロセスが使用中 | 既存 MySQL を止める／compose の `ports` を `"3307:3306"` にし、接続URLも `:3307` に |
| `command not found: uv` | 未インストール/PATH未反映 | ターミナルを開き直す。`uv --version` |
| `ModuleNotFoundError: No module named 'flask'` | `uv run` を付けずに実行した | `uv run flask ...` のように必ず `uv run` 経由で |

### DB 接続（SQLAlchemy / MySQL）

| エラー（抜粋） | 原因 | 対処 |
|---|---|---|
| `Can't connect to MySQL server on '127.0.0.1'` | MySQL 未起動、または起動途中 | `docker compose ps` で `healthy` を確認。まだなら数秒待つ |
| `Access denied for user 'flaskr'@'...'` | パスワード相違／**古いボリュームに旧設定が残存** | `docker compose down -v` → `up -d` で作り直す |
| `Unknown database 'flaskr_test'` | 初期化SQLが未実行 | Step 5 の initdb 追加後、`down -v` → `up -d` で再作成 |
| `No module named 'pymysql'` | ドライバ未導入 | `uv add pymysql`。接続URLが `mysql+pymysql://` か確認 |
| `Table 'flaskr.users' doesn't exist` | `init-db` 未実行 | `uv run flask --app flaskr init-db` |

### アプリ（Flask）

| エラー（抜粋） | 原因 | 対処 |
|---|---|---|
| `Could not locate a Flask application` | `--app flaskr` 指定漏れ/場所違い | `flaskr-api/` で `--app flaskr` を付けて実行 |
| `RuntimeError: Working outside of application context` | app context 外でDB操作 | `with app.app_context():` の中で実行（Step 2） |
| ログインが維持されない | CORS/credentials の3点セット欠け | Step 6 の①②③を全部確認 |
| Zed のブレークポイントで止まらない | `--no-reload` 未指定／port 不一致 | リロードを切る。`--listen` と `debug.json` の port を一致 |

---

## 7-2. まとめ（この教材で身についたこと）

| ステップ | 核心 |
|---|---|
| 0 | uv で Python 環境、Docker で MySQL、iTerm2 起動 + Zed attach デバッグ |
| 1 | `create_app()` ファクトリ、`@app.get`、辞書 return で JSON |
| 2 | SQLAlchemy モデル（クラス=テーブル）、`db.init_app`、MySQL 接続URL |
| 3 | Blueprint、パスワードハッシュ、`session`/`g`、`@login_required` 自作、CORS |
| 4 | CRUD + 認可（本人判定 403）、URL変数 `<int:>`、エラーJSON統一 |
| 5 | pytest フィクスチャ + `yield`、`test_client`、テスト用MySQL |
| 6 | 別オリジン + Cookie の3点セット、型付きAPIクライアント |

**Flask の設計思想（貫いていたこと）**:
- アプリは**関数が組み立てて返す成果物**（グローバル変数にしない）
- ルートは**デコレータで関数に貼る**、機能は**Blueprint で束ねる**
- 「明示は暗黙に勝る」— エラー処理も型もシリアライズも**書き手が書く**

---

## 7-3. 宿題（Lv1 → Lv2 → Lv3）

本編コードの続きとして解けます。各課題に**判定基準**と**折りたたみ解答**を付けています。

### Lv1（基礎確認）— 本編を少し変えれば解ける

#### 課題 1-A: `GET /posts/count` を追加

- **要件**: 記事の総数を `{"count": 3}` の形で返す
- **ヒント**: `db.session.scalar(db.select(db.func.count()).select_from(Post))`。Blueprint に1ルート足すだけ
- **判定基準**: 記事3件のとき `GET /posts/count` が `{"count":3}` を返す

<details><summary>解答例</summary>

```python
@bp.get("/count")
def count():
    n = db.session.scalar(db.select(db.func.count()).select_from(Post))
    return {"count": n}, 200
```
（`/posts/count` は `/<int:post_id>` より**先に**マッチする。文字列 `count` は `int` 変換に失敗するので衝突しないが、順序を意識するとより安全）
</details>

#### 課題 1-B: `password` の最低文字数バリデーション

- **要件**: `register` で `password` が8文字未満なら `400` + `{"error":"password too short"}`
- **ヒント**: `len(password) < 8`
- **判定基準**: 7文字で登録すると 400、8文字で 201

<details><summary>解答例</summary>

```python
    if len(password) < 8:
        return {"error": "password too short"}, 400
```
（`if not username or not password:` の直後に置く）
</details>

### Lv2（応用）— 本編の知識を組み合わせて自力実装

#### 課題 2-A: 記事にコメント機能を追加

- **要件**:
  - `Comment` モデル（`id`, `body`, `post_id`(FK), `author_id`(FK), `created`）を追加
  - `POST /posts/<id>/comments`（ログイン必須）でコメント作成 → 201
  - `GET /posts/<id>/comments` でそのコメント一覧
- **ヒント**: `Post` と `User` への `ForeignKey`/`relationship` は Step 2 と同型。モデル追加後は `flask init-db` で作り直し（or drop→create）
- **判定基準**: 記事にコメントを作成でき、一覧に反映される。未ログインの作成は 401

<details><summary>解答例（要点）</summary>

```python
# models.py
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User")
```

```python
# posts.py
@bp.post("/<int:post_id>/comments")
@login_required
def add_comment(post_id):
    post = get_post_or_404(post_id)
    data = request.get_json(silent=True) or {}
    body = data.get("body")
    if not body:
        return {"error": "body is required"}, 400
    c = Comment(body=body, post_id=post.id, author_id=g.user.id)
    db.session.add(c)
    db.session.commit()
    return {"id": c.id, "body": c.body}, 201


@bp.get("/<int:post_id>/comments")
def list_comments(post_id):
    get_post_or_404(post_id)
    rows = db.session.scalars(
        db.select(Comment).filter_by(post_id=post_id).order_by(Comment.created.desc())
    ).all()
    return [{"id": c.id, "body": c.body, "author": c.author.username} for c in rows], 200
```
</details>

### Lv3（発展）— 記事には無いが実務で必要な拡張

#### 課題 3: 一覧のページネーション + N+1 対策 + 入力バリデーションの統合

- **要件**:
  1. `GET /posts?limit=10&offset=0` でページング（既定 `limit=10`、上限 `50`）。レスポンスは `{"items":[...], "total": 42, "limit":10, "offset":0}`
  2. 一覧で著者を **N+1 なしで**取得（`joinedload`）
  3. `limit`/`offset` が数値でない/負なら `400`
- **ヒント**:
  - クエリ引数は `request.args.get("limit", default=10, type=int)`
  - 総数は `db.func.count`、本体は `.limit().offset()`
  - `db.select(Post).options(db.joinedload(Post.author))`
- **判定基準**:
  - `?limit=2` で最大2件、`total` は全件数
  - `?limit=abc` で 400
  - サーバーログ（Step 補足のSQLログ等）でクエリ数が記事数に比例しない

<details><summary>解答例（要点）</summary>

```python
@bp.get("")
def index():
    limit = request.args.get("limit", default=10, type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit is None or offset is None or limit < 0 or offset < 0:
        return {"error": "limit/offset must be non-negative integers"}, 400
    limit = min(limit, 50)

    total = db.session.scalar(db.select(db.func.count()).select_from(Post))
    posts = db.session.scalars(
        db.select(Post)
        .options(db.joinedload(Post.author))   # N+1 回避
        .order_by(Post.created.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [post_to_dict(p) for p in posts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }, 200
```
（`request.args.get(..., type=int)` は変換失敗時 `None` を返すので、それを 400 に落としている）
</details>

---

## 7-4. 発展（次に学ぶとよいこと）

| テーマ | なぜ | 入口 |
|---|---|---|
| **マイグレーション** | `create_all` は列追加を追跡できない。実務は必須 | Flask-Migrate（Alembic） |
| **設定の外出し** | パスワード/SECRET_KEY を git に載せない | `.env` + `python-dotenv`、`app.config.from_prefixed_env()` |
| **本番用サーバー** | `flask run` は開発用。本番は WSGI サーバー | gunicorn / uvicorn+asgi |
| **OpenAPI** | 型付きドキュメント & フロント型自動生成 | flask-smorest / spectree |
| **認証の発展** | セッションでなくトークンが要る場面 | JWT、リフレッシュトークン |
| **CI** | pushで自動テスト | GitHub Actions + MySQL サービスコンテナ |

---

## 7-5. 最終ブランクページ（総合再現）

エディタを閉じて、**白紙から最小構成を再現**してください。ファイル単位で挑戦し、詰まった行だけ該当ステップの 🔬 構文解剖 に戻ります。

再現対象:
1. `docker-compose.yml`（MySQL + volume + healthcheck）
2. `flaskr/__init__.py`（`create_app` + DB + CORS + Blueprint 登録 + errorhandler）
3. `flaskr/models.py`（`User`/`Post`）
4. `flaskr/auth.py`（`login_required` + register/login/logout/me）
5. `flaskr/posts.py`（CRUD + 認可）

全部を見ずに書けたら、この教材の目標「**実務でこのスタックを書ける**」に到達しています。

---

お疲れさまでした。Python の記号ひとつから、Docker・MySQL・認証・CRUD・テスト・フロント連携まで通しで組めるようになったはずです。
用語や文法で迷ったら [Appendix A: Python 基礎索引](./appendix-a-python-basics.md) を参照してください。
