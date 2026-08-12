# Step 0: 環境の土台を理解する（uv / Docker / MySQL）

← [目次](./README.md) ／ 次: [Step 1](./01-application-factory.md)

このステップは**手を動かす前の「地図」**です。3つの新しい道具を、**なぜ使うのか → 何なのか → どう使うのか**の順で丁寧に説明します。
Docker が初めてでも大丈夫。ここを読めば、あとのステップのコマンドが「おまじない」ではなく意味のある操作として理解できます。

> **これは核（環境理解）。** ここでつまずくと後が全部つらくなるので、時間をかける価値があります。

---

## 0-1. 全体像：この教材の環境はこう分かれている

```
┌─────────────────────────┐        ┌─────────────────────────┐
│ あなたのPC(ホスト)       │        │ Docker が動かすコンテナ  │
│                          │        │                          │
│  React (npm, :5173)      │        │  ┌───────────────────┐   │
│      │ fetch(JSON)       │        │  │ MySQL 8 (:3306)   │   │
│      ▼                   │        │  │ ＝ データベース    │   │
│  Flask (uv, :5000) ──────┼────────┼─▶│                   │   │
│      ▲                   │  接続   │  └───────────────────┘   │
│  （uv が Python と        │        │                          │
│    ライブラリを管理）     │        │  （docker compose で起動）│
└─────────────────────────┘        └─────────────────────────┘
```

- **React** と **Flask** は、あなたのPC上で直接動かします（速い・ログが見やすい・学習向き）
- **MySQL** だけを **Docker** の中で動かします

なぜ MySQL だけ Docker かというと、**データベースは自分のPCに直接インストールすると後片付けが大変**だからです。Docker なら「使う時だけ起動、要らなくなったら丸ごと削除」ができ、PCを汚しません。これは実務でも定番のやり方（＝「開発の依存物はコンテナ化、アプリ本体は手元で高速に回す」）です。

> 💡補足: 最終的には **Flask も Docker に入れて丸ごとコンテナ化**する方法も [Step 6](./06-frontend-and-wrapup.md) の「本番デプロイ」で紹介します。まずは学習しやすい上図の構成で進めます。

---

## 0-2. uv とは（Python 環境の管理ツール）

### なぜ使うのか
Python は昔から「仮想環境（venv）」「パッケージ管理（pip）」「Python 本体のバージョン管理」が**バラバラの道具**で、初心者がつまずく原因でした。
**uv** はこれらを**1つにまとめた高速なツール**（Rust 製）です。実務でも急速に普及しています。

| 従来 | uv での置き換え |
|---|---|
| `python -m venv .venv` + `source .venv/bin/activate` | 不要（`uv run` が自動で仮想環境を使う） |
| `pip install flask` | `uv add flask` |
| `python app.py` / `flask run` | `uv run python app.py` / `uv run flask run` |
| `requirements.txt` を手管理 | `pyproject.toml` + `uv.lock` を自動管理 |

### インストール
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# 入ったか確認
uv --version
```

### 覚える主要コマンドは4つだけ

| コマンド | 意味 |
|---|---|
| `uv init <名前>` | 新しい Python プロジェクトを作る（`pyproject.toml` などを生成） |
| `uv add <パッケージ>` | ライブラリを追加（pip install 相当。`pyproject.toml` にも自動記録） |
| `uv run <コマンド>` | プロジェクトの仮想環境で何かを実行（`flask run` 等）。**有効化(activate)は不要** |
| `uv sync` | `pyproject.toml`/`uv.lock` の内容どおりに環境を再現（他人のPCやCIで使う） |

> 🔗 **接続**: `uv run flask ...` は「その場だけ仮想環境を有効化してコマンドを実行する」イメージ。`source .venv/bin/activate` を毎回打つ手間がなくなります。

---

## 0-3. Docker とは（超入門）

### 一言でいうと
**「アプリと、それが動くのに必要な環境まるごとを、箱に詰めて持ち運べるようにする仕組み」**です。
「私のPCでは動くのに…」問題を無くすための技術、と考えてください。

### 3つの言葉だけ覚える

| 言葉 | 例え | 実際 |
|---|---|---|
| **イメージ (image)** | 料理の「レシピ＋材料セット」 | `mysql:8.0` のような、動かすための設計図（読み取り専用） |
| **コンテナ (container)** | レシピから作った「実際の料理」 | イメージを起動した、動いている実体。作って・止めて・捨てられる |
| **ボリューム (volume)** | 料理と別の「保存容器（冷蔵庫）」 | コンテナを消してもデータを残す保存領域。MySQLのデータ保存に使う |

**重要な性質**: コンテナは**使い捨て**が前提。消してもボリュームにデータがあれば安全。だから「壊れたら作り直す」が気軽にできます。

### 覚えておく2つの概念

- **ポート公開 (`3306:3306`)**: コンテナの中の 3306 番ポートを、あなたのPCの 3306 番につなぐ設定。これで PC 上の Flask が `localhost:3306` で MySQL に届く。
  - 書式は `"PC側:コンテナ側"`。もし PC の 3306 が埋まっていたら `"3307:3306"` のように左だけ変える
- **docker compose**: 複数のコンテナ（今回は MySQL）を **1つの設定ファイル `docker-compose.yml` にまとめて**、まとめて起動・停止する道具。手打ちの長い `docker run ...` を書かずに済む

### インストール
**Docker Desktop** を入れます（macOS/Windows）。[公式サイト](https://www.docker.com/products/docker-desktop/) からダウンロードして起動。
起動後、メニューバー（Mac）のクジラ🐳アイコンが「Running」になっていればOK。

```bash
# 入ったか確認
docker --version
docker compose version
# デーモン(本体)が動いているか確認（エラーが出たら Docker Desktop を起動する）
docker ps
```

> ⚠️ よくある最初のつまずき: `Cannot connect to the Docker daemon` と出たら、**Docker Desktop アプリ自体を起動**してください。CLI だけでは動きません。

---

## 0-4. MySQL を Docker で起動する設定ファイル

プロジェクト直下（`flaskr-api/`）に置く `docker-compose.yml` の中身を**1行ずつ**説明します。
（この教材の方針どおり、ファイルはあなたが自分で作成します。中身は下記をそのまま使えます）

`docker-compose.yml`:
```yaml
services:
  db:                                    # 「db」という名前のサービス(コンテナ)を1つ定義
    image: mysql:8.0                     # MySQL 8.0 の公式イメージを使う
    ports:
      - "3306:3306"                      # PCの3306 → コンテナの3306 につなぐ
    environment:                         # MySQL の初期設定を環境変数で渡す
      MYSQL_ROOT_PASSWORD: root          # 管理者(root)のパスワード
      MYSQL_DATABASE: flaskr             # 起動時に作るDB名（本番用）
      MYSQL_USER: flaskr                 # アプリが使うユーザー名
      MYSQL_PASSWORD: flaskr             # そのユーザーのパスワード
    command:                             # 文字コードを絵文字対応(utf8mb4)にする
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
    volumes:
      - mysql_data:/var/lib/mysql        # DBの中身を「mysql_data」ボリュームに永続化
      - ./docker/initdb:/docker-entrypoint-initdb.d  # 初回起動時に実行するSQL置き場
    healthcheck:                         # MySQLが「本当に受付可能」かを判定する設定
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uflaskr", "-pflaskr"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  mysql_data:                            # 上で使った永続ボリュームの宣言
```

さらに、**テスト用のDB**（`flaskr_test`）を初回起動時に自動で作るため、
`docker/initdb/01-init.sql` を作成します:

```sql
-- テスト専用のデータベースを作り、flaskr ユーザーに権限を与える
CREATE DATABASE IF NOT EXISTS flaskr_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON flaskr_test.* TO 'flaskr'@'%';
FLUSH PRIVILEGES;
```

**解説の要点:**
- `MYSQL_DATABASE: flaskr` で**本番用DB**が、`initdb` の SQL で**テスト用DB(`flaskr_test`)**が、起動時に自動作成される
- `volumes` の `mysql_data` があるので、コンテナを止めてもデータは消えない。逆に「データを完全リセット」したい時はボリュームごと消す（後述）
- `healthcheck` は「MySQL は起動プロセスが走ってから実際に接続を受けるまで数秒〜十数秒かかる」ため。これで「まだ準備中なのに繋ぎに行って失敗」を防げる

> ⚠️ `docker-entrypoint-initdb.d` の SQL は **ボリュームが空の初回起動時だけ**実行されます。後から SQL を変えても再実行されません。作り直したい時は `docker compose down -v`（ボリュームごと削除）してから起動し直します。

---

## 0-5. Docker の基本操作（この教材で使うのはこれだけ）

```bash
# MySQL を起動（-d はバックグラウンド実行。初回はイメージのダウンロードで数分かかる）
docker compose up -d

# 状態を確認（STATUS が "healthy" になれば接続OK。最初は "starting")
docker compose ps

# MySQL のログを見る（うまく起動しない時の調査に）
docker compose logs db

# 止める（データは残る）
docker compose stop

# 止めて後片付け（コンテナ削除。データ＝ボリュームは残る）
docker compose down

# 完全リセット（ボリュームごと削除。DBの中身も消える。作り直したい時）
docker compose down -v
```

> ⚠️ 下のコマンドを実際に動かすには、先に **0-4 の `docker-compose.yml` と `docker/initdb/01-init.sql` を `flaskr-api/` 直下に作成**しておく必要があります（無いと `no configuration file provided` エラー）。また `docker compose ...` は**そのファイルがあるディレクトリ（＝`flaskr-api/`）で実行**してください。

**🔮 予測 → 動作確認:** 「実行前に予想してみよう」——`docker compose up -d` の直後に `docker compose ps` を打つと、STATUS はいきなり `healthy` になる？

```bash
docker compose up -d
docker compose ps
```
期待される挙動: 最初は `starting`（または `health: starting`）、数十秒後にもう一度 `docker compose ps` すると `healthy` に変わります。**MySQL は起動に時間がかかる**ことを体感してください（Step2 で init-db する前に healthy を待つ理由）。

---

## ✅ 想起チェック

**見ないで説明してみよう:** 「イメージ」「コンテナ」「ボリューム」の関係を、料理の例えで説明できますか？ また、なぜ MySQL のデータはコンテナを消しても残せるのですか？

<details><summary>解答例</summary>

- **イメージ** = レシピ＋材料（設計図、読み取り専用）。**コンテナ** = レシピから作った実際の料理（動いている実体、使い捨て可）。**ボリューム** = 料理とは別の保存容器（永続データ置き場）。
- MySQL のデータ本体はコンテナ内ではなく **`mysql_data` ボリュームに保存**しているため。コンテナ（料理）を捨てても、ボリューム（保存容器）が残っていればデータは失われない。完全に消すには `docker compose down -v` でボリュームごと削除する。
</details>

**小問:** `ports: "3306:3306"` の左と右はそれぞれ何を指す？ PCの3306番が既に使われていたらどう直す？

<details><summary>解答例</summary>

書式は `"PC側:コンテナ側"`。左 `3306` があなたのPCのポート、右 `3306` がコンテナ内のMySQLのポート。PCの3306が埋まっていたら**左だけ**変える（例 `"3307:3306"`）。その場合 Flask の接続先も `localhost:3307` に変更する。
</details>

---

準備ができたら [Step 0.5: クエリログ整形 & Zed デバッグ](./00.5-debug-and-query-logs.md) へ（アプリを書く前に開発の「見る道具」を仕込みます）。以降のコマンドは `uv run ...`、DB は Docker の MySQL を使います。
