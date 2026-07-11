# Flask 公式チュートリアル → React + Flask REST API 実践教材

> 元記事: [Flask Tutorial (公式)](https://flask.palletsprojects.com/en/3.0.x/tutorial/)
> 元記事は「Flaskr」というブログアプリを **Jinja テンプレート + 生 sqlite3** で作ります。
> この教材では同じ題材を、実務で主流の構成に置き換えて作ります:
> - フロント: **React + TypeScript**
> - バック: **Flask + SQLAlchemy** の REST API
> - DB: **MySQL**（**Docker** で起動）
> - Python 環境: **uv** で管理
>
> 👉 Docker が初めての人は、まず [Step 0: 環境の土台（uv / Docker / MySQL）](./00-docker-uv-mysql.md) を読んでください。ここで環境の全体像を丁寧に説明しています。

---

## 0. 概要 — この教材で学べること

Flask 公式チュートリアルの「Flaskr（ブログアプリ）」を題材に、次を身につけます。

- **アプリケーションファクトリ**で Flask アプリを組み立てる（設定・拡張の登録を関数に集約する）
- **Blueprint** で機能ごとにルートを分割する（`auth` と `blog`）
- **SQLAlchemy** でモデルを定義し、DB を読み書きする（元記事の生 SQL を ORM に置換）
- **セッション Cookie 認証**（登録・ログイン・ログアウト・ログイン必須ガード）を JSON API として実装する
- **CRUD REST API**（記事の一覧・作成・更新・削除）を、認可（本人のみ編集可）付きで作る
- **pytest** でテストを書き、テストクライアントで API を検証する

学習スタイルは「**見る → 写す → 消す → 記憶から再現**」。
序盤は写経、中盤は穴埋め（`# TODO`）、終盤は要件だけを見て自力実装 → 折りたたみで答え合わせ、と提示量を減らしていきます。

---

## 1. 完成物の全体像（先に到達点を知る）

最終的に、React フロントが叩ける次の JSON API を作ります。

| メソッド | パス | 説明 | 認証 |
|---|---|---|---|
| `POST` | `/auth/register` | ユーザー登録 | 不要 |
| `POST` | `/auth/login` | ログイン（セッション Cookie を発行） | 不要 |
| `POST` | `/auth/logout` | ログアウト | 不要 |
| `GET`  | `/auth/me` | ログイン中のユーザー情報 | 任意 |
| `GET`  | `/posts` | 記事一覧（新しい順） | 不要 |
| `POST` | `/posts` | 記事作成 | 必須 |
| `GET`  | `/posts/<id>` | 記事1件 | 不要 |
| `PUT`  | `/posts/<id>` | 記事更新（著者のみ） | 必須 |
| `DELETE` | `/posts/<id>` | 記事削除（著者のみ） | 必須 |

---

## 2. 元記事との対応・スタック置き換え表（重要）

元記事は別スタックなので、**要点（＝Flask の設計思想）を保ったまま**下表のように置き換えます。
各ステップ本文でも、置き換えた箇所には `🔁 置き換え` を付けて明記します。

| 元記事（Flaskr） | この教材 | なぜ置き換えるか |
|---|---|---|
| 生 `sqlite3` + `schema.sql` + `db.execute(...)` | **Flask-SQLAlchemy**（モデルクラス + `db.session`） | 実務では ORM が主流。型・リレーションが扱いやすい |
| `render_template()` + Jinja テンプレート | **JSON を返す** → 画面は **React** が描く | フロント/バック分離の REST API にするため |
| `flash()`（画面にメッセージ表示） | **JSON のエラーボディ** `{"error": "..."}` + HTTP ステータス | API はメッセージを JSON で返す |
| `redirect(url_for(...))` | **JSON レスポンス + ステータスコード**（201 など） | API はリダイレクトせず結果を返す |
| `request.form['username']` | **`request.get_json()`** | React は JSON ボディを送る |
| `login_required` → ログイン画面へ redirect | `login_required` → **401 JSON を返す** | API はページ遷移しない |
| （同一オリジンで Cookie 自動送信） | **Flask-CORS** で別オリジン + Cookie 送信を許可 | React(5173) と Flask(5000) はオリジンが違う |
| **SQLite**（ファイル1個のDB） | **MySQL 8**（**Docker** で起動） | 実務で主流の本格的なRDB。同時接続・本番運用に強い |
| `venv` + `pip` | **uv**（環境・依存・Python 本体を一括管理） | 実務で普及中の高速ツール。環境構築のつまずきを減らす |
| （DB を直接インストール） | **Docker Compose** で MySQL を起動 | PCを汚さず、作り直し・破棄が容易 |

> 💡補足: 「置き換える」といっても、Flask 側の **設計（ファクトリ / Blueprint / `g` / `session` / `before_app_request` / エラー処理）はすべて元記事のまま**残します。学ぶ核はそこにあるからです。

---

## 3. 前提知識・環境

**前提知識（あると理解が速い）**
- React で `fetch`/`useState`/`useEffect` を使ったことがある
- SQL の基本（`SELECT` / `INSERT` を見て意味が分かる程度でOK）
- Python の関数・デコレータの読み書き（`@decorator` の形を見たことがある）

**必要なツール / バージョン**（インストール手順は [Step 0](./00-docker-uv-mysql.md) 参照）

| ツール | バージョン目安 | 用途 |
|---|---|---|
| **uv** | 0.4 以上 | Python 本体・仮想環境・依存を一括管理（pip/venv の置き換え） |
| **Docker Desktop** | 最新 | MySQL をコンテナで起動 |
| Node.js | 18 以上 | React フロント |
| curl | 任意 | API の動作確認 |

> 💡補足: **Python は個別インストール不要**です。uv が必要な Python バージョンを自動で用意します。**MySQL も個別インストール不要**（Docker が起動します）。

**使う Python パッケージ**（`uv add` で入れる）

| パッケージ | 役割 |
|---|---|
| `flask` | 本体 |
| `flask-sqlalchemy` | ORM（DB 操作） |
| `flask-cors` | React からの Cookie 付きリクエストを許可 |
| `pymysql` | MySQL 接続ドライバ（Python から MySQL に繋ぐ） |
| `cryptography` | MySQL 8 の認証方式に必要（PyMySQL が内部で使用） |
| `python-dotenv` | `.env` から設定を自動読み込み |
| `pytest`（開発用） | テスト |

---

## 4. 環境構築

> ⚠️ ここでは「動く準備」だけ整えます。**アプリ本体のファイルは各ステップで自分の手で書きます**（雛形は配りません）。
> ルートは `flaskr-api/` という作業ディレクトリを想定します。
> 👉 uv・Docker の**意味**は [Step 0](./00-docker-uv-mysql.md) で説明済み。ここでは実際に手を動かします。

### 4-1. バックエンドの土台（uv）

```bash
# 1) uv でプロジェクトを作成（pyproject.toml / .venv などを自動生成）
uv init flaskr-api
cd flaskr-api

# 2) 依存パッケージを追加（pip install 相当。pyproject.toml に自動記録される）
uv add flask flask-sqlalchemy flask-cors pymysql cryptography python-dotenv

# 3) テスト用パッケージは開発依存として追加（本番には含めない）
uv add --dev pytest

# 4) uv init が作った雛形 main.py は使わないので消してよい
rm -f main.py

# 5) Flask アプリ本体を入れるパッケージの箱を作る（__init__.py を置く箱）
mkdir flaskr
```

各コマンドの意味:
- `uv init flaskr-api` … プロジェクトを作成。`python3 -m venv` + `pip` の初期化をまとめて実施。仮想環境の**手動 activate は不要**（以降 `uv run` が自動で使う）
- `uv add ...` … ライブラリを追加し `pyproject.toml` と `uv.lock` に記録。`Python が無ければ uv が自動で用意`
- `uv add --dev pytest` … テスト専用（本番デプロイには含めない）依存として追加
- `mkdir flaskr` … Flask アプリ本体のパッケージ（中身は Step1 で書く）

### 4-2. データベースの土台（Docker + MySQL）

[Step 0](./00-docker-uv-mysql.md#0-4-mysql-を-docker-で起動する設定ファイル) の `docker-compose.yml` と `docker/initdb/01-init.sql` を `flaskr-api/` 直下に作成し、起動します。

```bash
# Docker Desktop を起動しておくこと（🐳 が Running）
docker compose up -d          # MySQL コンテナを起動（初回はイメージDLで数分）
docker compose ps             # STATUS が "healthy" になれば接続OK（最初は starting）
```

- 本番用DB `flaskr` とテスト用DB `flaskr_test` が自動で作られます
- 接続情報は `mysql+pymysql://flaskr:flaskr@localhost:3306/flaskr`（Step1 で `.env` に書きます）

### 4-3. フロントエンドの土台（React + TypeScript）

```bash
# flaskr-api/ の中で実行。Vite で React+TS プロジェクトを作成
npm create vite@latest frontend -- --template react-ts

cd frontend
npm install
npm run dev    # http://localhost:5173 が立ち上がればOK（今は確認だけ）
cd ..
```

- `npm create vite@latest ... --template react-ts` … Vite の React+TypeScript テンプレートを生成
- `npm run dev` … 開発サーバ（デフォルト `http://localhost:5173`）を起動

> 💡補足: 最終的なディレクトリ構成の目安
> ```
> flaskr-api/
> ├── .venv/               ← uv が管理（触らない）
> ├── pyproject.toml       ← 依存の記録（uv add が更新）
> ├── uv.lock              ← 依存の固定（uv が管理）
> ├── .env                 ← 接続情報・秘密鍵（Step1で作成／Git管理外）
> ├── docker-compose.yml   ← MySQL の起動定義（Step0）
> ├── docker/
> │   └── initdb/01-init.sql  ← テスト用DBを作るSQL（Step0）
> ├── flaskr/              ← Flask アプリ本体（Step1〜4で書く）
> │   ├── __init__.py      ← アプリケーションファクトリ
> │   ├── models.py        ← SQLAlchemy モデル
> │   ├── auth.py          ← 認証 Blueprint
> │   └── blog.py          ← 記事 Blueprint
> ├── tests/               ← pytest（Step5で書く）
> └── frontend/            ← React（Step6で連携）
> ```
>
> 💡補足: `.gitignore` に `.venv/`・`.env`・`__pycache__/` を入れておきましょう（秘密情報と生成物をコミットしないため）。

---

## 5. 進め方（目次）

**上から順に**進めてください。各ステップは前のステップに積み上がります。

| Step | ファイル | 内容 | 提示量 |
|---|---|---|---|
| 0 | [00-docker-uv-mysql.md](./00-docker-uv-mysql.md) | 環境の土台（uv / Docker / MySQL の入門） | 読み物 |
| 1 | [01-application-factory.md](./01-application-factory.md) | アプリケーションファクトリと最初のルート | 写経（完成形） |
| 2 | [02-database-sqlalchemy.md](./02-database-sqlalchemy.md) | SQLAlchemy でモデル定義・DB 初期化 | 写経〜一部穴埋め |
| 3 | [03-auth-api.md](./03-auth-api.md) | 認証 API（登録・ログイン・ログアウト・ガード） | 穴埋め（`# TODO`） |
| 4 | [04-blog-api.md](./04-blog-api.md) | 記事 CRUD API（認可付き） | 要件のみ→自力 |
| 5 | [05-testing.md](./05-testing.md) | pytest でテスト | 要件のみ→自力 |
| 6 | [06-frontend-and-wrapup.md](./06-frontend-and-wrapup.md) | React 連携・つまずき・まとめ・**宿題**・発展 | — |

各ステップには必ず次が入っています:
- 🎯 **目的** と「**核 / 補足**」の区別
- 💻 **コード**（段階的に提示量を減らす）
- 🧠 **解説**（なぜそう書くか。React/Django の知識と接続）
- 🔮 **予測 → 動作確認**（実行前に出力を予想 → コマンド → 期待される出力）
- ✅ **想起チェック**（見ないで説明 / 小問。答えは折りたたみ）

では [Step 0: 環境の土台](./00-docker-uv-mysql.md) へ（Docker が初めてでなければ [Step 1](./01-application-factory.md) から始めてもOK）。
