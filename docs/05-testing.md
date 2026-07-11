# Step 5: pytest でテスト

← [Step 4](./04-blog-api.md) ／ [目次](./README.md) ／ 次: [Step 6](./06-frontend-and-wrapup.md)

## 🎯 目的

pytest の **フィクスチャ**（`app` / `client` / `auth`）を用意し、テストクライアントで API を検証する。
各ビューの正常系と、認証・認可（401/403/404）の分岐を押さえる。

> **核: フィクスチャの設計**（テスト専用 DB を作り、テストごとに使い捨てる）と、**分岐を網羅する**という考え方。
> **補足: カバレッジ計測**（`coverage`）。あれば安心だが、まずはテストが書けることが先。

🔁 **置き換え**:
- 元記事は `tests/data.sql` を流し込んでいた → **フィクスチャ内で SQLAlchemy モデルを直接 `add`** してシードする
- テストは HTML（`response.data` にバイト列が含まれるか）ではなく、**JSON（`response.get_json()`）とステータスコード**で検証する
- `auth.login()` は `data=`（フォーム）ではなく **`json=`** で送る
- 元記事は一時 SQLite ファイルをテスト用DBにしていた → この教材は **Docker MySQL 内の専用DB `flaskr_test`** を使い、**各テストで `drop_all()`→`create_all()`** して初期化する（本番と同じ MySQL でテストするので、方言差による見落としが減る）

> ⚠️ **前提**: テストも MySQL を使うので、`docker compose up -d` で MySQL が `healthy` である必要があります。テスト用DB `flaskr_test` は [Step0](./00-docker-uv-mysql.md) の `docker/initdb/01-init.sql` で作成済みです。

このステップも**終盤なので要件先行**。フィクスチャの解答例だけ先に渡し、各テストは自分で書いてから照合します。

---

## 💻 フィクスチャ（土台なので解答を提示・写経）

まず `.env` に**テスト用DBの接続先**を追記します（本番 `flaskr` とは別DB `flaskr_test`）:

```bash
# .env に追記
TEST_DATABASE_URL=mysql+pymysql://flaskr:flaskr@localhost:3306/flaskr_test?charset=utf8mb4
```

`tests/conftest.py` を新規作成:

```python
import os

import pytest
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from flaskr import create_app
from flaskr.models import db, User, Post

# pytest は Flask CLI と違い .env を自動で読まないので、明示的に読み込む
load_dotenv()


@pytest.fixture
def app():
    # テスト専用の MySQL データベース(flaskr_test)に接続する
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": os.environ["TEST_DATABASE_URL"],
    })

    with app.app_context():
        # 前のテストの残骸を消してから作り直す → 毎テスト同じ初期状態に
        db.drop_all()
        db.create_all()

        u1 = User(username="test", password=generate_password_hash("test"))
        u2 = User(username="other", password=generate_password_hash("other"))
        db.session.add_all([u1, u2])
        db.session.commit()
        db.session.add(Post(title="test title", body="test\nbody", author_id=u1.id))
        db.session.commit()

    yield app

    # 後片付け: テーブルを全部落として次のテストに残骸を残さない
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class AuthActions:
    """ログイン/ログアウトを毎回書かずに済ませるヘルパー。"""
    def __init__(self, client):
        self._client = client

    def login(self, username="test", password="test"):
        return self._client.post(
            "/auth/login", json={"username": username, "password": password}
        )

    def logout(self):
        return self._client.post("/auth/logout")


@pytest.fixture
def auth(client):
    return AuthActions(client)
```

**解説:**
- `app` フィクスチャは `create_app({...})` に **テスト用設定**を渡す。Step1 で `test_config` を受け取れるようにしたのがここで効く
- 🔁 SQLite の一時ファイルは使えないので、**MySQL の `flaskr_test` DB を `drop_all()`→`create_all()` で毎回まっさらに**する。これで**テスト間が独立**する（前のテストのデータが残らない）
- `os.environ["TEST_DATABASE_URL"]` … `.env` の値を読む。conftest 冒頭の `load_dotenv()` が pytest 実行時に `.env` を環境変数へ読み込む
- `test_client()` は**サーバを起動せずに**リクエストを送れる。Cookie も内部で保持するので、`auth.login()` 後のリクエストはログイン状態が続く
- `auth` フィクスチャは pytest が**引数名の一致**で自動注入する（`def test_x(auth):` と書くだけ）

> 💡補足（速度と本番一致のトレードオフ）: MySQL でのテストは「本番と同じDB＝方言差の見落としが減る」利点がある一方、SQLite in-memory より遅めです。CI や高速フィードバックを優先するなら、テストだけ `SQLALCHEMY_DATABASE_URI="sqlite:///:memory:"` に切り替える手もあります（ただし MySQL 固有挙動は検証できません）。学習目的では本番と同じ MySQL を推奨します。

---

## 📋 要件（自分で書く）

`pyproject.toml`（無ければ新規）に追記:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["flaskr"]
```

次の3ファイルを書く。まず自力で、その後に折りたたみと照合。

**`tests/test_auth.py`**
- `test_register`: `POST /auth/register` に新規ユーザーで 201。DB にそのユーザーが存在する
- `test_register_validate`: 空 username→400、既存 username→400（`pytest.mark.parametrize` で複数ケース）
- `test_login`: ログイン後、`GET /auth/me` が `{"id":1,"username":"test"}` を返す
- `test_login_bad`: 誤 username→400、誤 password→400
- `test_logout`: ログアウト後、`GET /auth/me` が `{"user": null}`

**`tests/test_blog.py`**
- `test_index`: `GET /posts` に `"test title"` の記事が含まれる
- `test_login_required`: 未ログインで `POST /posts`・`PUT /posts/1`・`DELETE /posts/1` は 401
- `test_author_required`: 記事1の著者を `other` に変え、`test` でログイン → `PUT/DELETE /posts/1` は 403
- `test_exists_required`: `PUT/DELETE /posts/999` は 404
- `test_create`: ログイン → `POST /posts` で記事が1件増える
- `test_update`: ログイン → `PUT /posts/1` で title が変わる
- `test_delete`: ログイン → `DELETE /posts/1` で 204、DB から消える

> ヒント（考え方のみ）:
> - JSON の中身は `response.get_json()`（dict/list が返る）。ステータスは `response.status_code`
> - DB を直接確認するときは `with app.app_context():` の中で `db.session.get(Post, 1)` や `Post.query.count()`
> - 著者を書き換えるテストは、`app_context` 内で `post.author_id = 2; db.session.commit()`

<details><summary>解答例（tests/test_auth.py）</summary>

```python
import pytest

from flaskr.models import db, User


def test_register(client, app):
    res = client.post("/auth/register", json={"username": "a", "password": "a"})
    assert res.status_code == 201

    with app.app_context():
        assert User.query.filter_by(username="a").first() is not None


@pytest.mark.parametrize(("username", "password", "message"), (
    ("", "", "Username is required."),
    ("a", "", "Password is required."),
    ("test", "test", "already registered"),
))
def test_register_validate(client, username, password, message):
    res = client.post("/auth/register", json={"username": username, "password": password})
    assert res.status_code == 400
    assert message in res.get_json()["error"]


def test_login(client, auth):
    assert auth.login().status_code == 200
    res = client.get("/auth/me")
    assert res.get_json() == {"id": 1, "username": "test"}


@pytest.mark.parametrize(("username", "password", "message"), (
    ("a", "test", "Incorrect username."),
    ("test", "a", "Incorrect password."),
))
def test_login_bad(auth, username, password, message):
    res = auth.login(username, password)
    assert res.status_code == 400
    assert message in res.get_json()["error"]


def test_logout(client, auth):
    auth.login()
    auth.logout()
    assert client.get("/auth/me").get_json() == {"user": None}
```
</details>

<details><summary>解答例（tests/test_blog.py）</summary>

```python
import pytest

from flaskr.models import db, Post


def test_index(client):
    res = client.get("/posts")
    titles = [p["title"] for p in res.get_json()]
    assert "test title" in titles


@pytest.mark.parametrize("method_path", (
    ("post", "/posts"),
    ("put", "/posts/1"),
    ("delete", "/posts/1"),
))
def test_login_required(client, method_path):
    method, path = method_path
    res = getattr(client, method)(path, json={"title": "x"})
    assert res.status_code == 401


def test_author_required(app, client, auth):
    # 記事1の著者を other(id=2) に変える
    with app.app_context():
        post = db.session.get(Post, 1)
        post.author_id = 2
        db.session.commit()

    auth.login()  # test(id=1) でログイン
    assert client.put("/posts/1", json={"title": "x"}).status_code == 403
    assert client.delete("/posts/1").status_code == 403


@pytest.mark.parametrize("path", ("/posts/999",))
def test_exists_required(client, auth, path):
    auth.login()
    assert client.put(path, json={"title": "x"}).status_code == 404
    assert client.delete(path).status_code == 404


def test_create(client, auth, app):
    auth.login()
    res = client.post("/posts", json={"title": "created", "body": ""})
    assert res.status_code == 201
    with app.app_context():
        assert Post.query.count() == 2


def test_update(client, auth, app):
    auth.login()
    res = client.put("/posts/1", json={"title": "updated", "body": ""})
    assert res.status_code == 200
    with app.app_context():
        assert db.session.get(Post, 1).title == "updated"


def test_delete(client, auth, app):
    auth.login()
    res = client.delete("/posts/1")
    assert res.status_code == 204
    with app.app_context():
        assert db.session.get(Post, 1) is None
```
</details>

<details><summary>解答例（tests/test_factory.py）</summary>

```python
from flaskr import create_app


def test_config():
    assert not create_app().testing
    assert create_app({"TESTING": True}).testing


def test_hello(client):
    res = client.get("/hello")
    assert res.data == b"Hello, World!"
```
</details>

---

## 🔮 予測 → 動作確認

**実行前に予想してみよう。**
- 何個のテストがパスする？（数えてみる）
- もし `login_required` を付け忘れていたら、どのテストが落ちる？
- MySQL を止めた状態で実行したら？（→ 接続エラーで全滅する）

```bash
# MySQL が healthy であること（docker compose ps）を確認してから
uv run pytest
```

> 💡補足: `uv run pytest` は uv の仮想環境で pytest を実行します。`pyproject.toml` に `flaskr` パッケージがある（uv プロジェクト）ので、`ModuleNotFoundError: No module named 'flaskr'` は起きません。

期待される出力（件数は書いた数による。全て緑ならOK）:
```
tests/test_auth.py ......                     [ ... ]
tests/test_blog.py .........                   [ ... ]
tests/test_factory.py ..                       [100%]
==================== NN passed in 0.xx s ====================
```

カバレッジも見るなら:
```bash
uv add --dev coverage
uv run coverage run -m pytest
uv run coverage report
```
`flaskr/*.py` の Cover が高い（100% 近い）ほど、分岐まで検証できている証拠です。

> 💡補足: もし `test_author_required` が落ちたら、`get_post` の著者チェック（403）や `login_required`（401 が先に出ていないか）を疑います。テストは「どのステップの実装が崩れたか」を教えてくれるレーダーです。

---

## ✅ 想起チェック

**見ないで説明してみよう:** `app` フィクスチャが「各テストで `drop_all()`→`create_all()` し、`yield` の後にも `drop_all()` する」構造になっているのはなぜ？

<details><summary>解答例</summary>

テスト間の**独立性**を保つため。あるテストで作成・削除した記事が別テストに影響すると、実行順で結果が変わる「不安定なテスト」になる。MySQL は SQLite の一時ファイルのように使い捨てできないので、テストごとに `flaskr_test` DB のテーブルを**全削除→再作成**して、各テストを同じ初期状態（シードデータ）から始める。`yield` 後の `drop_all()` で残骸も残さない。
</details>

**小問:** 元記事の `tests/data.sql` は、この教材では何に置き換わった？

<details><summary>解答例</summary>

`app` フィクスチャ内で **SQLAlchemy モデルを直接 `db.session.add(...)` してシードする**コードに置き換わった。`User`/`Post` のインスタンスを作って commit することで、生 SQL ファイルを使わずに初期データを用意している。
</details>

---

次は [Step 6: React 連携・まとめ・宿題](./06-frontend-and-wrapup.md)。
