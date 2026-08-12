# Step 5: pytest で API をテストする

← [Step 4](./04-blog-api.md) ／ [目次](./README.md) ／ 次: [Step 6](./06-frontend.md)

**作るもの**: pytest とテストクライアントで、認証・CRUD・認可を自動テストする。テストは**専用の MySQL テストDB**で回す
**重要度**: 🔴 **毎日書く**（テストは実務の必須スキル。テストしやすい設計＝良い設計）
**前ステップとの接続**: `create_app` を「設定を差し替えられる」形に少し改造し、テスト用DBを注入する

> 🔁 **置き換え**: 公式は sqlite のテストDBを使う。この教材は**sqlite を使わない**方針なので、
> Docker の MySQL コンテナ内に**テスト専用データベース `flaskr_test`** を用意し、そこでテストする。

---

## 5-1. まず `create_app` を「設定注入できる」形にする

テストでは本番用DB(`flaskr`)ではなく、テスト用DB(`flaskr_test`)に繋ぎたい。
そこで `create_app(test_config=None)` と**引数で設定を上書きできる**ようにします。

**ファイル: `flaskr-api/flaskr/__init__.py`（設定注入対応・全文）**

```python
from flask import Flask
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .models import db


def create_app(test_config=None):
    app = Flask(__name__)

    # 既定（本番/開発）の設定
    app.config.from_mapping(
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI=(
            "mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr"
        ),
    )

    # テスト時は渡された設定で上書き
    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    CORS(
        app,
        resources={r"/*": {"origins": ["http://localhost:5173"]}},
        supports_credentials=True,
    )

    from .auth import bp as auth_bp
    from .posts import bp as posts_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return {"error": e.description, "status": e.code}, e.code

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
```

### 🔬 構文解剖: `test_config=None`（デフォルト引数）

| 部品 | 読み方 | 意味 |
|---|---|---|
| `test_config=None` | — | **デフォルト引数**。呼び出し時に省略すると `None` が入る |
| `None` | ノン | 「値が無い」を表す特別値（JS の `null` 相当） |

**効果**: 通常起動 `create_app()` は `None` → 本番設定。テストは `create_app({...})` で上書き設定を渡せる。
**既知スタックとの対応**: JS の `function createApp(testConfig = null)`。引数のデフォルト値と同じ。

### 🔬 構文解剖: `app.config.from_mapping(...)` と `app.config.update(...)`

| 部品 | 意味 |
|---|---|
| `from_mapping(KEY=値, ...)` | 複数の設定をまとめて登録する。キーワード引数で並べる |
| `app.config.update({...})` | 辞書で設定を上書きする（既存キーは置き換え） |

**なぜ2段か**: まず既定を敷き、テスト時だけ必要分を上書きする「デフォルト→オーバーライド」の型。設定管理の定番。

---

## 5-2. テスト用DB `flaskr_test` を用意する

MySQL コンテナ起動時に、テスト用DBも自動で作られるよう**初期化SQL**を追加します。

**ファイル: `flaskr-api/docker/initdb/01-init.sql`（新規）**

```sql
-- テスト用データベースを作成し、flaskr ユーザーに権限を付与する
CREATE DATABASE IF NOT EXISTS flaskr_test;
GRANT ALL PRIVILEGES ON flaskr_test.* TO 'flaskr'@'%';
FLUSH PRIVILEGES;
```

これを compose から**コンテナ初回起動時に流し込む**設定を足します。

**ファイル: `flaskr-api/docker-compose.yml`（`db` サービスに volumes を1行追加）**

```yaml
    volumes:
      - db-data:/var/lib/mysql
      - ./docker/initdb:/docker-entrypoint-initdb.d   # ★追加
```

### 🔬 構文解剖: `/docker-entrypoint-initdb.d`

| 部品 | 意味 |
|---|---|
| `./docker/initdb:/docker-entrypoint-initdb.d` | ホストの `docker/initdb` を、コンテナの特別ディレクトリにマウント |
| `/docker-entrypoint-initdb.d` | **mysql イメージの約束事**。ここに置いた `.sql`/`.sh` を**初回起動時に自動実行**する |

**⚠️ 重要**: この初期化は**ボリュームが空の初回だけ**走る。既にデータがあると実行されない。
なので追加後は一度作り直す:

```bash
docker compose down -v      # ボリュームごと削除（-v）
docker compose up -d        # 作り直し → 01-init.sql が走る
```

**既知スタックとの対応**: 「初回シード用スクリプトを置く場所」。多くのDBイメージが持つ規約で、React には対応物なし（インフラ側の概念）。

確認:

```bash
docker compose exec db mysql -u flaskr -pflaskr -e "SHOW DATABASES;"
# flaskr と flaskr_test の両方が見えれば成功
```

---

## 5-3. テストの下準備（pytest 導入と conftest）

```bash
uv add --dev pytest
```

pytest は「`test_` で始まる関数」を自動でテストとして集めて実行します。
共通の準備（アプリ生成・DB初期化・クライアント）は `conftest.py` に**フィクスチャ**として書きます。

**ファイル: `flaskr-api/tests/conftest.py`（新規・全文）**

```python
import pytest

from flaskr import create_app
from flaskr.models import db

TEST_DB_URI = "mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr_test"


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": TEST_DB_URI,
        }
    )

    # 各テストの前に「まっさらなテーブル」を用意する
    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    # テスト後に後片付け
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """HTTPを立てずにアプリを叩けるテストクライアント。"""
    return app.test_client()
```

### 🔬 構文解剖: `@pytest.fixture`

| 部品 | 意味 |
|---|---|
| `@pytest.fixture` | デコレータ。この関数を**テストの前準備部品(fixture)**として登録する |
| 関数名 `app` / `client` | フィクスチャの名前。テスト関数が**同名の引数**で受け取ると、pytest が自動で用意して渡す |

**しくみ**: `def test_xxx(client):` と書くと、pytest が `client` フィクスチャを実行して結果を注入する。**依存性注入**の仕組み。
**既知スタックとの対応**: Jest の `beforeEach` + 共有セットアップを、引数で受け取る形にしたもの。

### 🔬 構文解剖: `yield app`（フィクスチャの前後処理）

| 部品 | 読み方 | 意味 |
|---|---|---|
| `yield` | イールド | 関数の実行を**一旦ここで止めて値を返す**。テスト終了後に続きが再開する |
| `yield` の**前** | — | テスト前の準備（テーブル作成） |
| `yield` の**後** | — | テスト後の後片付け（テーブル削除） |

**効果**: `yield app` で `app` をテストに渡し、テストが終わると `yield` の下（後片付け）が走る。**setup/teardown を1関数**に書ける。
**既知スタックとの対応**: `beforeEach`/`afterEach` を1つにまとめた形。`yield` は「関数を途中で中断・再開できる」Python の仕組み（ジェネレータ）。

### 🔬 構文解剖: `app.test_client()`

| 部品 | 意味 |
|---|---|
| `test_client()` | 実際にネットワークサーバーを立てずに、アプリへHTTPリクエストを送れる疑似クライアント |

**なぜ使うか**: `uv run flask run` でサーバーを起動しなくても、`client.post("/auth/login", ...)` で API を叩ける。速く・確実にテストできる。
**既知スタックとの対応**: `supertest`（Express テスト）の `request(app).post(...)` に相当。

---

## 5-4. テストを書く（完成 → 穴埋め）

**ファイル: `flaskr-api/tests/test_auth.py`（完成形・写経）**

```python
def register(client, username="alice", password="pw12345"):
    return client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )


def test_register_then_me(client):
    res = register(client)
    assert res.status_code == 201
    assert res.get_json()["username"] == "alice"

    # 登録直後はまだログインしていない
    res = client.get("/auth/me")
    assert res.get_json()["user"] is None


def test_duplicate_register_conflicts(client):
    register(client)
    res = register(client)
    assert res.status_code == 409


def test_login_sets_session(client):
    register(client)
    res = client.post(
        "/auth/login",
        json={"username": "alice", "password": "pw12345"},
    )
    assert res.status_code == 200

    res = client.get("/auth/me")
    assert res.get_json()["user"]["username"] == "alice"
```

### 🔬 構文解剖: `assert 条件`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `assert 条件` | アサート | 条件が**偽なら失敗**（AssertionError）にする。pytest はこれで合否を判定 |
| `res.status_code` | — | テストクライアントの応答ステータス |
| `res.get_json()` | — | 応答ボディを辞書として取り出す |
| `json={...}` | — | `client.post` の引数。**辞書を JSON ボディとして送る**（`Content-Type` も自動付与） |

**既知スタックとの対応**: Jest の `expect(x).toBe(y)` を、素の `assert` で書く感覚。pytest は `assert` の式を解析して失敗時に差分を見せてくれる。
**なぜ `client` はログイン状態を保てるか**: `test_client()` は**Cookie を自動で保持**する。`login` で受けたセッションCookieを、次の `client.get("/auth/me")` に自動で送るため、同一クライアント内でログイン状態が続く。

### 課題: `tests/test_posts.py` を自力で書く

**要件（穴埋めではなく要件のみ）:**
- ログインしてから記事を作成 → `201`、`author.username == "alice"`
- ログインせず作成 → `401`
- 他人(`bob`)の記事を更新 → `403`
- 本人が削除 → `204`、その後 `GET` は `404`

**判定基準**: `uv run pytest` が全部 pass する。

<details><summary>解答例</summary>

```python
def register_and_login(client, username="alice", password="pw12345"):
    client.post("/auth/register", json={"username": username, "password": password})
    client.post("/auth/login", json={"username": username, "password": password})


def create_post(client, title="t", body="b"):
    return client.post("/posts", json={"title": title, "body": body})


def test_create_requires_login(client):
    res = create_post(client)
    assert res.status_code == 401


def test_create_and_list(client):
    register_and_login(client)
    res = create_post(client, title="hello")
    assert res.status_code == 201
    assert res.get_json()["author"]["username"] == "alice"

    res = client.get("/posts")
    data = res.get_json()
    assert isinstance(data, list)
    assert data[0]["title"] == "hello"


def test_cannot_update_others_post(client):
    # alice が作成
    register_and_login(client, "alice")
    post_id = create_post(client).get_json()["id"]
    client.post("/auth/logout")

    # bob がログインして更新を試みる
    register_and_login(client, "bob")
    res = client.put(f"/posts/{post_id}", json={"title": "x", "body": "y"})
    assert res.status_code == 403


def test_delete_then_404(client):
    register_and_login(client)
    post_id = create_post(client).get_json()["id"]

    res = client.delete(f"/posts/{post_id}")
    assert res.status_code == 204

    res = client.get(f"/posts/{post_id}")
    assert res.status_code == 404
```

**ポイント**: `isinstance(data, list)` は「一覧がJSON配列か」の確認。`f"/posts/{post_id}"` は**f-string**（次の解剖）。
</details>

### 🔬 構文解剖: f-string `f"/posts/{post_id}"`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `f"..."` | エフ文字列 | **f-string**。文字列前に `f` を付けると `{式}` を埋め込める |
| `{post_id}` | — | 波カッコの中の変数/式が文字列に展開される |

**既知スタックとの対応**: JS のテンプレートリテラル `` `/posts/${postId}` ``。バッククォートの代わりに `f"..."`、`${}` の代わりに `{}`。

---

## 5-5. 実行する

```bash
# flaskr-api/ で（MySQL 起動済みが前提）
uv run pytest -v
```

### 🔮 実行前に予想しよう
- 各テストは前のテストのデータを引きずる？引きずらない？（`conftest` の `yield` 前後を思い出す）

<details><summary>答え</summary>

引きずらない。`app` フィクスチャが**各テストの前に `drop_all()`→`create_all()`** し、後で `drop_all()` する。テストごとにDBがまっさらになるので独立している。
</details>

### 期待される出力（要点）

```
tests/test_auth.py::test_register_then_me PASSED
tests/test_auth.py::test_duplicate_register_conflicts PASSED
tests/test_auth.py::test_login_sets_session PASSED
tests/test_posts.py::... PASSED
====== N passed in X.XXs ======
```

---

## 5-6. 🏢 実務メモ / ⚠️ アンチパターン

### 🏢 実務メモ
「テストしやすい設計＝良い設計」。`create_app(test_config)` で設定を注入できるようにしたことで、DBを差し替えてテストできた。
実務では CI（GitHub Actions 等）で **MySQL サービスコンテナを立てて `pytest`** を回す。ローカルと同じ「Docker の MySQL」を CI でも使えば環境差が出にくい。

### ⚠️ やりがち
> **やりがち**: テスト間でDBを消さず、前のテストのデータが残って別テストが落ちる/たまたま通る。
> **現場では**: テストごとに独立させる（`drop_all/create_all` かトランザクションのロールバック）。テストの独立性は鉄則。

---

## 5-7. ✅ 想起チェック

<details><summary>Q1. フィクスチャの `yield` の前と後には、それぞれ何を書く？</summary>

前＝テスト前の準備（テーブル作成など）、後＝テスト後の後片付け（テーブル削除など）。`yield` でテストに値を渡し、終了後に続きが走る。
</details>

<details><summary>Q2. なぜ `test_client()` はログイン状態を保てる？</summary>

テストクライアントが Cookie を自動保持するから。`login` で得たセッションCookieを後続リクエストに自動送信する。
</details>

<details><summary>Q3. テストDBに sqlite ではなく `flaskr_test`(MySQL) を使うのはなぜ？</summary>

本番と同じ MySQL 方言でテストして差異を減らすため（この教材の方針）。`docker-entrypoint-initdb.d` の初期化SQLで自動作成した。
</details>

---

## ✍️ ブランクページ（章末の再現）

`conftest.py` を閉じて白紙から再現:

- `app` フィクスチャ（`create_app({TESTING, URI})` → `drop_all/create_all` → `yield` → 後片付け）
- `client` フィクスチャ（`app.test_client()`）
- 認証テストを1本（register → 201 → me が null）

---

## まとめ

- `create_app(test_config)` で**設定注入**できる形にした（テスト容易性）
- テストDBは Docker MySQL 内の `flaskr_test`（初期化SQLで自動作成）
- `@pytest.fixture` + `yield` で setup/teardown、`test_client()` で API を直接叩く
- `assert` で合否、テストは**各テスト独立**（毎回DBリセット）

次の [Step 6](./06-frontend.md) で、React + TypeScript から**Cookie 付き `fetch`** でこの API を叩きます。
