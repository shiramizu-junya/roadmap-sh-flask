# Step 0: 環境の土台を理解する（uv / Docker / MySQL / iTerm2 / Zed）

← [目次](./README.md) ／ 次: [Step 1](./01-application-factory.md)

**このステップで作るもの**: MySQL を Docker で起動し、Python(Flask) を uv で動かし、Zed でブレークポイントを止められる状態
**重要度**: 🔴 **毎日書く**（環境の考え方は毎回使う。ここでつまずくと後が全部つらい）
**前提**: React/TS の経験あり。Docker と Python は初めてでもOK

このステップは**手を動かす前の「地図」**です。新しい道具を、**なぜ使うのか → 何なのか → どう使うのか**の順で説明します。
ここを読めば、後のステップのコマンドが「おまじない」ではなく意味のある操作として理解できます。

---

## 0-1. 全体像：この教材の環境はこう分かれる

```
┌────────────────────────────────┐        ┌──────────────────────────┐
│ あなたのPC（＝ホスト）          │        │ Docker が動かすコンテナ   │
│                                 │        │                          │
│  React     (npm,  :5173) ──┐    │        │  ┌────────────────────┐  │
│                            │    │        │  │ MySQL 8  (:3306)   │  │
│                     fetch(JSON) │        │  │  ＝ データベース    │  │
│                            ▼    │        │  │                    │  │
│  Flask     (uv,   :5000) ───────┼────────┼─▶│  データはボリューム │  │
│      ▲                          │  接続   │  │  に永続化           │  │
│  debugpy   (      :5678)        │        │  └────────────────────┘  │
│      ▲ アタッチ                 │        │                          │
│  Zed（ブレークポイント）         │        │  docker compose で起動   │
└────────────────────────────────┘        └──────────────────────────┘
```

- **React と Flask はあなたのPC上で直接動かす**（速い・ログが見やすい・デバッグしやすい＝学習向き）
- **MySQL だけを Docker の中で動かす**（PCに MySQL を直接インストールしなくて済む。要らなくなったら消せる）
- **Zed は debugpy(:5678) 経由で、iTerm2 で動かしている Flask にアタッチ**してブレークポイントを張る

> 🧠 **この教材の考え方**: 「実行するもの（Flask/React）」と「保存するもの（MySQL）」を分ける。
> DBだけコンテナに閉じ込めておくと、PCの環境が汚れず、壊れてもコンテナを作り直すだけで戻せる。

登場する3つの道具の役割を先に一言で:

| 道具 | 一言でいうと | React でいう何に近い？ |
|---|---|---|
| **uv** | Python本体とライブラリのバージョンを管理し、実行する道具 | `npm` + `node` のバージョン管理（nvm）を1つにした感じ |
| **Docker** | アプリを「箱（コンテナ）」に入れて、PCを汚さず動かす道具 | 対応物なし（フロントには無い概念）。後述 |
| **MySQL** | データを保存する本格的なリレーショナルDB | 対応物なし（Supabase/Firestore の“DB本体”側） |

---

## 0-2. uv：Python の環境管理

### 0-2-1. なぜ uv を使うのか（pip / venv ではなく）

Python は「PC本体に入っている Python」を直接使うと、プロジェクトごとにライブラリのバージョンが衝突して壊れます。
そこで**プロジェクト専用の隔離環境（仮想環境, virtual environment）**を作るのが常識です。従来は `venv`（環境を作る）と `pip`（入れる）を別々に使いましたが、この教材では**uv 1本**にまとめます。

> 🔁 **置き換え**: 公式チュートリアルは `python -m venv` + `pip` を使う。この教材は **uv** に置き換える。
> 理由: 依存解決が桁違いに速く、`uv run` を使えば「仮想環境を有効化する（activate）」操作を意識せず実行できるため。

> 💡 **補足**: uv は Rust 製の Python パッケージ/プロジェクト管理ツール。
> React でいうと、`node` のバージョン管理（nvm/volta）と `npm`（依存管理）と `npx`（実行）を**1つのコマンドに統合**したものが近い。

### 0-2-2. インストールと確認

```bash
# uv をインストール（macOS）
curl -LsSf https://astral.sh/uv/install.sh | sh

# ターミナルを開き直してから確認
uv --version
```

### 🔬 構文解剖: `curl -LsSf https://astral.sh/uv/install.sh | sh`

| 部品 | 読み方 | 意味 |
|---|---|---|
| `curl` | カール | URL からデータを取得するコマンド |
| `-L` | エル | リダイレクトを追う（配布URLが転送されても最終先まで取りに行く） |
| `-s` | エス | silent。進捗バーを出さない |
| `-S` | 大エス | silent でもエラーだけは表示する |
| `-f` | エフ | サーバーが 404 等を返したら失敗扱いにする（壊れたスクリプトを実行しない安全策） |
| `\|` | パイプ | 左の出力を右のコマンドの入力に渡す記号 |
| `sh` | シェル | 受け取ったスクリプトをそのまま実行する |

**既知スタックとの対応**: `curl ... \| sh` は「インストールスクリプトを取ってきて実行」。npm でいう公式インストーラを叩くのと同じ発想。
**なぜここでこれを選ぶか**: uv 公式が推奨する方法。Homebrew(`brew install uv`)でも入るが、最新版が最も早く届くのは公式スクリプト。

### 0-2-3. プロジェクトを作る

```bash
# 作業したい場所へ移動（例）
cd ~/workspace

# uv プロジェクトを新規作成（ディレクトリごと作られる）
uv init flaskr-api

cd flaskr-api
```

`uv init` を実行すると、`flaskr-api/` の中に次が生成されます。

| 生成物 | 役割 | React でいうと |
|---|---|---|
| `pyproject.toml` | プロジェクト設定と依存ライブラリの一覧 | `package.json` |
| `.python-version` | このプロジェクトで使う Python のバージョン | `.nvmrc` |
| `main.py`（またはサンプル） | ひな形の実行ファイル（後で消してよい） | エントリの雛形 |
| `README.md` | 説明ファイル | 同じ |

> 💡 **補足**: `uv init` の直後にはまだ `.venv/`（仮想環境の実体）はありません。
> 後で `uv add` や `uv run` を初めて実行したとき、uv が自動で `.venv/` を作り、Python本体も必要なら取得します。

### 0-2-4. ライブラリを追加する

このステップではまだ Flask を「動作確認用」に入れておきます（本格利用は Step 1）。

```bash
uv add flask
```

### 🔬 構文解剖: `uv add flask` と pyproject.toml の中身

`uv add flask` を実行すると `pyproject.toml` の `dependencies` に1行増えます。

```toml
# pyproject.toml（抜粋。uv add が自動で書き込む）
[project]
name = "flaskr-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.0",
]
```

| 部品 | 読み方 | 意味 |
|---|---|---|
| `[project]` | ブラケット project | **テーブル**（TOMLのセクション見出し）。この下の行が「プロジェクト設定」だと示す |
| `name = "..."` | — | `キー = 値`。TOML の代入。文字列は必ずダブルクォート |
| `requires-python` | — | このプロジェクトが必要とする Python のバージョン制約 |
| `dependencies = [ ... ]` | — | 角カッコ `[]` は**リスト**（配列）。依存ライブラリを並べる |
| `"flask>=3.0"` | — | 「flask をバージョン 3.0 以上で」の意味。`>=` は「以上」 |

**既知スタックとの対応**: `pyproject.toml` の `dependencies` は `package.json` の `dependencies`。`uv add` は `npm install --save`。
**なぜ TOML なのか**: TOML(Tom's Obvious Minimal Language)は設定ファイル用の形式。JSON よりコメントが書けて人が読みやすいため、Python 界隈の標準設定形式になっている。

### 🔬 構文解剖: `uv run`（後で何度も使う最重要コマンド）

```bash
uv run python --version    # 仮想環境の中の Python を実行
```

| 部品 | 意味 |
|---|---|
| `uv run` | 「このプロジェクトの仮想環境の中で」続くコマンドを実行する。実行前に依存を自動で同期(sync)する |
| `python --version` | 実際に実行したいコマンド |

**既知スタックとの対応**: `npm run` や `npx` に近い。`.venv` を手動で `activate` しなくても、`uv run` を頭に付ければ隔離環境で動く。
**なぜここでこれを選ぶか**: 「仮想環境を有効化し忘れて、PC本体の Python で動かしてしまう」という初学者の典型事故を防げる。この教材ではサーバー起動もテストも**全部 `uv run` 経由**にする。

### 🏢 実務メモ
`pyproject.toml`（何を入れたか）と `uv.lock`（実際に入った正確なバージョン）は**両方 git にコミット**する。
`uv.lock` があるとチーム全員・CI が寸分違わぬバージョンで動く（`package-lock.json` と同じ役割）。`.venv/` は `.gitignore` に入れてコミットしない（`node_modules/` と同じ）。

### ⚠️ やりがち
> **やりがち**: `uv run` を付け忘れて `python app.py` と打ち、PC本体の Python で動いて「ライブラリが無い」エラーになる。
> **現場では**: 実行は常に `uv run ...`。もしくは `source .venv/bin/activate` で明示的に有効化する。この教材は前者で統一する。

---

## 0-3. Docker：MySQL を「箱」に入れて動かす

### 0-3-1. なぜ Docker を使うのか

MySQL のようなDBを**PC本体に直接インストール**すると、次の問題が起きます。

- インストールが OS ごとに違って面倒（設定ファイル、起動サービス、初期ユーザー…）
- バージョンを上げ下げしにくい。要らなくなっても綺麗に消しにくい
- チームで「私のPCでは動く」問題が起きる

Docker は、**アプリ（ここでは MySQL）を必要な設定ごと「箱」に閉じ込めて、どのPCでも同じように動かす**道具です。
DBを箱に入れておけば、**PC本体は一切汚れず**、壊れたら箱を捨てて作り直すだけで復旧できます。

> 🧠 **考え方**: Docker は「動かし方をコード（設定ファイル）に固定する」道具。
> React でいうと `node_modules` を各人が入れる代わりに、**OSごと丸ごと固めて配る**イメージ。フロント開発には無い概念なので、下の用語を先に押さえる。

### 0-3-2. 用語（⚪ 背景知識だが、知らないとエラーが読めない）

| 用語 | 読み方 | 意味 | たとえ |
|---|---|---|---|
| **image**（イメージ） | イメージ | 箱の「設計図・雛形」。`mysql:8.0` など。読み取り専用 | クラスの定義 / Docker版の「インストーラ」 |
| **container**（コンテナ） | コンテナ | イメージから起動した「実際に動いている箱」 | クラスから作ったインスタンス |
| **volume**（ボリューム） | ボリューム | コンテナの外にデータを保存する保管庫。コンテナを消してもデータが残る | 外付けディスク |
| **port**（ポート） | ポート | 箱の中と外(PC)をつなぐ通信の口。`3306` など | 建物のドア番号 |
| `docker compose` | コンポーズ | 複数コンテナの構成を1ファイル(`docker-compose.yml`)にまとめて一括起動する仕組み | `package.json` の scripts でまとめ実行 |

> ⚠️ **重要**: コンテナは「使い捨て」。コンテナを消すと**中に書いたデータも消える**のが原則。
> だからDBのデータは必ず **volume** に逃がして永続化する（後述の設定でやる）。

### 0-3-3. Docker Desktop のインストールと確認

Docker Desktop（Mac版）を https://www.docker.com/products/docker-desktop/ からインストールし、**起動しておく**（メニューバーにクジラのアイコンが出る）。

```bash
docker --version         # インストール確認
docker compose version   # compose が使えるか確認
```

> ⚠️ Docker Desktop の**アプリ自体を起動していないと** `docker` コマンドは「Cannot connect to the Docker daemon」で失敗する。まずクジラのアイコンを確認。

---

## 0-4. docker-compose.yml で MySQL を起動する

`flaskr-api/` の直下に `docker-compose.yml` を作ります。**ファイル名はこの通りにする**（`docker compose` はこの名前を探す）。

**ファイル: `flaskr-api/docker-compose.yml`（全文）**

```yaml
services:
  db:
    image: mysql:8.0
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: flaskr
      MYSQL_USER: flaskr
      MYSQL_PASSWORD: flaskr
    volumes:
      - db-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-prootpass"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  db-data:
```

### 🔬 構文解剖: docker-compose.yml（YAML の記法とキー）

まず YAML そのものの読み方から（**この教材で初めて出る記法**）。

| 記法 | 読み方 | 意味 |
|---|---|---|
| インデント（半角スペース） | — | **入れ子（階層）を表す**。タブは禁止。スペース2個ずつが慣習。ここが YAML 最大の落とし穴 |
| `キー:` | コロン | `キー: 値` のペア。コロンの後ろに**半角スペース**が要る |
| `- 値` | ハイフン | **リストの1要素**。同じインデントの `-` が並ぶと配列になる |
| `"3306:3306"` | — | 文字列。`:` を含む値はクォートで囲むと安全 |

次に各キーの意味:

| キー | 意味 |
|---|---|
| `services:` | 起動するコンテナ群の定義。この下の `db:` が1つのサービス（コンテナ）名 |
| `db:` | サービス名（自分で決める任意の名前）。他コンテナからは `db` というホスト名で参照できる |
| `image: mysql:8.0` | 使うイメージ（設計図）。`mysql` の `8.0` タグ。無ければ自動DL |
| `ports: - "3306:3306"` | **`ホスト側:コンテナ側`**。PC の 3306 番を、箱の中の MySQL(3306) につなぐ。左が自分のPC |
| `environment:` | コンテナに渡す環境変数。mysql イメージはこれを読んで初期ユーザー/DBを作る |
| `MYSQL_DATABASE: flaskr` | 起動時に自動で作るデータベース名 |
| `MYSQL_USER` / `MYSQL_PASSWORD` | 一般ユーザーを1つ作る。この教材の Flask はこのユーザーで接続する |
| `MYSQL_ROOT_PASSWORD` | 管理者(root)のパスワード |
| `volumes: - db-data:/var/lib/mysql` | **`ボリューム名:コンテナ内パス`**。MySQL がデータを書く `/var/lib/mysql` を `db-data` に永続化 |
| `healthcheck:` | 「DBが本当に受付可能か」を定期チェックする設定。次の Step で「起動待ち」に使う |
| 一番下の `volumes: db-data:` | 使うボリュームの宣言。ここで名前を登録して初めて上の参照が有効になる |

**既知スタックとの対応**: `docker-compose.yml` は「複数プロセスの起動設定を宣言的に書く」もの。`package.json` の scripts より宣言的で、React には直接の対応物がない。
**なぜ `ports` の左右があるか**: 箱の中と外はネットワークが別。`3306:3306` と書いて初めて、PC から `127.0.0.1:3306` で箱の中の MySQL に届く。
**なぜ healthcheck を書くか**: MySQL はコンテナ起動後、実際に接続を受け付けるまで数秒かかる。その「準備完了」を機械的に判定するため。

> 💡 **補足（環境変数を直書きしていることについて）**: ここではパスワードを YAML に直書きしている。
> **実務では** これらは `.env` ファイルや Secrets 管理に外出しし、`docker-compose.yml` には書かない（git に乗せない）。
> 本教材は学習用に見やすさ優先で直書きしている。Step 7 で `.env` 化を扱う。

### 0-4-1. 起動する

```bash
# flaskr-api/ の中で実行
docker compose up -d
```

### 🔬 構文解剖: `docker compose up -d`

| 部品 | 意味 |
|---|---|
| `docker compose` | `docker-compose.yml` を読んでコンテナ群を操作する |
| `up` | 定義したサービスを起動する（イメージが無ければDL→コンテナ作成→起動） |
| `-d` | detached。**バックグラウンドで**起動し、ターミナルを返す（付けないとログで占有される） |

**関連コマンド**（この教材で使う分）:

| コマンド | 何をするか |
|---|---|
| `docker compose ps` | 起動中のコンテナと状態(healthy か)を一覧 |
| `docker compose logs -f db` | `db` のログを追いかけ表示（`-f` は follow）。`Ctrl+C` で抜ける |
| `docker compose down` | コンテナを止めて削除する（**ボリュームは残る**＝データは消えない） |
| `docker compose down -v` | コンテナ**とボリュームも**削除（`-v`）。DBを初期化したいとき |

### 🔮 実行前に予想しよう
`docker compose up -d` の直後に `docker compose ps` を打つと、`db` の状態は何と出るはず？
（ヒント: MySQL は起動してすぐ受付可能にはならない。healthcheck の結果は最初どうなる？）

<details><summary>答え合わせ</summary>

初回はイメージ `mysql:8.0` のダウンロードで少し時間がかかる。起動直後の `ps` では `health: starting`（準備中）と出て、数秒〜十数秒後にもう一度打つと `healthy` に変わる。`healthy` になれば接続可能。
</details>

### 0-4-2. 本当に接続できるか確認

```bash
# 箱の中の mysql クライアントに入って、flaskr ユーザーで接続
docker compose exec db mysql -u flaskr -pflaskr flaskr -e "SELECT 1 AS ok;"
```

**期待される出力:**

```
+----+
| ok |
+----+
|  1 |
+----+
```

### 🔬 構文解剖: `docker compose exec db mysql -u flaskr -pflaskr flaskr -e "..."`

| 部品 | 意味 |
|---|---|
| `docker compose exec db` | 起動中の `db` コンテナの**中で**続くコマンドを実行する |
| `mysql` | コンテナ内の MySQL クライアント |
| `-u flaskr` | user。接続ユーザー名 |
| `-pflaskr` | password。**`-p` とパスワードの間にスペースを空けない**のが mysql の作法（空けると別の意味になる） |
| `flaskr`（3つ目） | 接続先のデータベース名 |
| `-e "SELECT 1 AS ok;"` | execute。1行SQLを実行してすぐ抜ける。`AS ok` は結果列に `ok` という別名を付ける |

**これが出れば**: 箱の中で MySQL が起動し、`flaskr` ユーザー・`flaskr` DB が作られ、接続できている。土台OK。

---

## 0-5. iTerm2 でサーバーを起動しながら Zed でブレークポイントを張る

ここがあなたの狙いです。「**iTerm2 で Flask を動かしっぱなしにして、Zed でコードにブレークポイントを張って止める**」を実現します。

### 0-5-1. しくみ（attach 方式）

Python のデバッグは **debugpy**（デバッグ用アダプタ）を使います。やり方は2通り:

| 方式 | 何をするか | この教材 |
|---|---|---|
| **launch** | Zed が自分でサーバーを起動して、そのままデバッグ | 使わない |
| **attach** | あなたが iTerm2 で起動したサーバーに、Zed が**後から接続**してデバッグ | ✅ **これを使う** |

あなたの希望（iTerm2 で起動しながら Zed で止める）は **attach 方式**そのものです。
流れ: iTerm2 で `debugpy` を待ち受け付きで Flask を起動 → Zed が `:5678` にアタッチ → Zed でブレークポイントに止まる。

### 0-5-2. debugpy を入れる

```bash
uv add --dev debugpy
```

### 🔬 構文解剖: `uv add --dev debugpy`

| 部品 | 意味 |
|---|---|
| `--dev` | 開発時だけ使う依存として追加する（本番の実行には不要なもの） |
| `debugpy` | Microsoft 製の Python デバッグアダプタ。Zed/VSCode 等はこれ経由でデバッグする |

**既知スタックとの対応**: `npm install --save-dev`。本番に要らない開発ツールを分けて管理するのは同じ。
**なぜ dev か**: デバッガは本番サーバーには要らないため。分けておくと本番ビルドが軽くなる。

### 0-5-3. iTerm2 でサーバーを起動する

> ⚠️ この時点ではまだ Flask アプリ本体（`flaskr` パッケージ）を作っていないので、**下のコマンドが実際に通るのは Step 1 以降**です。
> ここでは「起動コマンドの形」と各部品の意味を先に理解しておきます（Step 1 の 🔮 で実際に走らせます）。

iTerm2 を開き、`flaskr-api/` で次を実行します。

```bash
uv run python -m debugpy --listen 5678 --wait-for-client -m flask --app flaskr run --no-reload
```

### 🔬 構文解剖: debugpy 付き Flask 起動コマンド

| 部品 | 読み方 | 意味 |
|---|---|---|
| `uv run` | — | プロジェクトの仮想環境で以下を実行（0-2 参照） |
| `python -m debugpy` | ハイフンエム | `-m` は「モジュールをスクリプトとして実行」。`debugpy` をコマンドとして起動する |
| `--listen 5678` | — | debugpy を **5678番ポートで待ち受け**にする。Zed はここへ繋ぐ |
| `--wait-for-client` | — | **Zed がアタッチするまで実行を止めて待つ**。最初の1行目から確実に止めたいときに有効 |
| `-m flask` | — | debugpy が起動する対象。`flask` モジュールを実行する（=`flask` CLI） |
| `--app flaskr` | — | ここから先は flask への引数。「`flaskr` パッケージがアプリ」だと教える |
| `run` | — | flask のサブコマンド。開発サーバーを起動 |
| `--no-reload` | — | ファイル変更時の自動リロードを**切る**。理由は下記 |

**`-m` を2回使う入れ子の意味**: `python -m debugpy ... -m flask ...` は「debugpy を起動し、その debugpy に『flask モジュールを動かして』と渡す」という二段構え。前半が「デバッグの器」、`-m flask` 以降が「その中で動かす中身」。

**なぜ `--no-reload` か**: Flask の自動リロードは、コードを保存すると**プロセスを別プロセスに作り直す**。すると debugpy が繋いでいたプロセスが消えてブレークポイントが外れる。だからデバッグ中はリロードを切る。
**既知スタックとの対応**: `--listen`+attach は、Node で `node --inspect` して Chrome DevTools を繋ぐのと同じ発想（プロセスを起動しておき、デバッガが後から繋ぐ）。

起動すると、こう表示されてカーソルが止まります（`--wait-for-client` で Zed 待ち）:

```
（何も進まず待機。Zed からアタッチすると先へ進む）
```

### 0-5-4. Zed 側の設定（アタッチ構成）

プロジェクト直下に `.zed/debug.json` を作ります。**フォルダ名 `.zed`・ファイル名 `debug.json` はこの通り**（Zed がこの場所を探す）。

**ファイル: `flaskr-api/.zed/debug.json`（全文）**

```json
[
  {
    "label": "Flask: 起動中サーバーにアタッチ",
    "adapter": "Debugpy",
    "request": "attach",
    "tcp_connection": { "host": "127.0.0.1", "port": 5678 }
  }
]
```

### 🔬 構文解剖: `.zed/debug.json`

| 部品 | 意味 |
|---|---|
| 一番外の `[ ... ]` | JSON の配列。**複数のデバッグ構成を並べられる**。今は1個 |
| `{ ... }` | 1つのデバッグ構成 |
| `"label"` | Zed のデバッグUIに表示される名前（自由に付けてよい） |
| `"adapter": "Debugpy"` | 使うデバッグアダプタ。Python は `Debugpy`（大文字D、Zed の表記） |
| `"request": "attach"` | **アタッチ方式**を選ぶ（起動中プロセスに繋ぐ）。`"launch"` なら Zed が起動する |
| `"tcp_connection"` | 繋ぎ先の指定。**オブジェクト形式** `{ "host": ..., "port": ... }` |
| `"host": "127.0.0.1"` | 自分のPC（ローカルホスト）を指す |
| `"port": 5678` | iTerm2 で `--listen 5678` にした番号と**一致させる**（ここがズレると繋がらない） |

**なぜ `attach` / この port か**: iTerm2 で `--listen 5678` した debugpy に Zed が繋ぐため、番号を合わせる。`host` は同じPC内なので `127.0.0.1`。
**既知スタックとの対応**: VSCode の `.vscode/launch.json` と同じ役割のファイル。Zed 版が `.zed/debug.json`。

### 0-5-5. ブレークポイントを張って止める手順

1. iTerm2 で 0-5-3 のコマンドを実行（Zed 待ちで止まる）
2. Zed で、止めたい行の**行番号の左（ガター）をクリック**して赤丸（ブレークポイント）を付ける
3. Zed のコマンドパレット（`Cmd+Shift+P`）で **`debugger: start`** を実行 → 構成 `Flask: 起動中サーバーにアタッチ` を選ぶ（`F4` でも起動メニューが出る）
4. アタッチ成功すると iTerm2 の Flask が動き出す
5. その行を通るリクエストを投げる（例: ブラウザや `curl` で API を叩く）と、Zed がその行で**実行を止める**。変数の値を見たり、1行ずつ実行（ステップ実行）できる

> 💡 **補足**: `--wait-for-client` を外すと、サーバーは Zed を待たずに起動する。
> その場合は「先に iTerm2 でサーバーを普通に動かしておき、デバッグしたくなった時だけ Zed からアタッチ」という運用になる。学習中は付けておくと「最初から確実に止まる」ので分かりやすい。

### 🏢 実務メモ
attach 方式は、**本番に近い起動方法のままデバッグできる**のが利点（起動コマンドをデバッガ用に変えなくてよい）。
実務では「再現しにくいバグを、動いているプロセスに後から繋いで調べる」ときにこの方式が効く。ローカルでは launch 方式（Zed が起動）の方が手数は少ないので、慣れたら使い分ける。

### ⚠️ やりがち
> **やりがち**: `--no-reload` を付け忘れ、コード保存のたびにブレークポイントが外れて「止まらない」と悩む。
> **現場では**: デバッグセッション中はリロードを切る。コードを直したら一度デバッグを止め、サーバーを起動し直してから再アタッチする。

---

## 0-6. つまずきポイント（エラー全文 → 原因 → 対処）

| エラー（抜粋） | 原因 | 対処 |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop アプリが起動していない | メニューバーのクジラを確認し、起動してから再実行 |
| `Bind for 0.0.0.0:3306 failed: port is already allocated` | PC で別の MySQL が 3306 を使用中 | 既存 MySQL を止める／`ports` を `"3307:3306"` に変え、接続も 3307 にする |
| `Access denied for user 'flaskr'@'...'` | パスワード相違、または**既存ボリュームに古い設定が残っている** | `docker compose down -v` でボリュームごと消し、`up -d` で作り直す |
| `command not found: uv` | uv 未インストール、またはPATH未反映 | ターミナルを開き直す。`uv --version` を確認 |
| Zed のアタッチが `connection refused` | サーバー未起動、または port 不一致 | iTerm2 のコマンドが待機中か確認。`--listen` と `debug.json` の port を一致させる |

---

## ✅ 想起チェック

見ないで答えてみましょう（答えは折りたたみ）。

1. なぜ MySQL を Docker の中で動かし、Flask は PC 上で直接動かすのか？
2. `docker-compose.yml` の `ports: "3306:3306"` の**左と右**はそれぞれ何を指す？
3. コンテナを消してもDBのデータが消えないようにしているのはどのキー？
4. Zed でブレークポイントを止めるとき、iTerm2 側の `--listen` の番号と `.zed/debug.json` の何を一致させる必要がある？

<details><summary>答え</summary>

1. 「保存するもの(MySQL)」を箱に閉じ込めると PC 環境が汚れず、壊れても作り直せるから。「実行するもの(Flask/React)」は速さとデバッグのしやすさのため PC 上で直接動かす。
2. 左=あなたのPC(ホスト)側のポート、右=コンテナの中の MySQL のポート。`ホスト:コンテナ`。
3. `volumes:`（`db-data:/var/lib/mysql`）。データをコンテナ外のボリュームに永続化している。
4. `port`（5678）。`--listen 5678` と `debug.json` の `"port": 5678` を一致させる。
</details>

---

## ✍️ ブランクページ（章末の再現練習）

エディタを閉じて、**白紙から** `docker-compose.yml` を再現してみましょう。
思い出せなかった行に印を付け、その行の `🔬 構文解剖`（0-4）だけ読み返します。

再現の合格ライン（最低限これが書けていれば土台は理解できている）:

- `services:` の下に `db:` があり `image: mysql:8.0`
- `ports` に `"3306:3306"`
- `environment` に `MYSQL_DATABASE` / `MYSQL_USER` / `MYSQL_PASSWORD`
- `volumes` でデータを永続化している
- 一番下に `volumes:` の宣言がある

---

## まとめ（このステップで手に入れたもの）

- **uv** で Python プロジェクトを作り、`uv run` で隔離環境の中で実行できる
- **Docker** の image / container / volume / port の意味が分かった
- **MySQL** を `docker compose up -d` で起動し、接続確認できた
- **iTerm2 で起動 → Zed でアタッチ**してブレークポイントを張る仕組み（attach 方式）を用意できた

次の [Step 1](./01-application-factory.md) で、いよいよ Flask アプリ本体（`flaskr` パッケージ）を**アプリケーションファクトリ**で組み立て、最初の REST ルートを動かします。
