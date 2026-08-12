# Step 6: React + TypeScript から Cookie 付きで API を叩く

← [Step 5](./05-testing.md) ／ [目次](./README.md) ／ 次: [Step 7](./07-wrapup.md)

**作るもの**: Vite の React + TS アプリから、ログイン・記事一覧・記事作成を行う画面
**重要度**: 🟡 **読めればよい**（React/TS はあなたの既知分野。**新しいのは「別オリジン + Cookie の fetch」と CORS の噛み合わせ**なのでそこを厚く）
**前ステップとの接続**: Step 3 で `supports_credentials=True` にした CORS と、フロントの `credentials:"include"` を対応させる

> このステップは、あなたが既に知っている React/TS の文法は解剖しません（`useState` 等は説明済み前提）。
> 代わりに **Flask API と React をつなぐ境界**（CORS・セッションCookie・fetch のオプション）を重点的に分解します。

---

## 6-1. 最重要概念：別オリジン間で Cookie を運ぶ3点セット

フロント(`localhost:5173`)とAPI(`localhost:5000`)は**ポートが違う＝別オリジン**です。
セッションCookie（Step 3）をこの境界で往復させるには、**3つが全部そろう**必要があります。1つでも欠けるとログインが維持できません。

| # | どこ | 何を設定 | 役割 |
|---|---|---|---|
| 1 | フロントの `fetch` | `credentials: "include"` | リクエストに Cookie を**乗せて送る/受け取る** |
| 2 | サーバーの CORS | `supports_credentials=True`（Step 3 で設定済み） | 「Cookie 付きを受け付ける」と応答ヘッダで宣言 |
| 3 | サーバーの CORS | `origins` に**具体的なURL**（`*` 不可） | Cookie 付きのとき送信元を明示する必要がある |

```
┌ React :5173 ─────────┐                 ┌ Flask :5000 ──────────┐
│ fetch(url, {          │  ①Cookie送信    │ CORS:                  │
│   credentials:        │ ───────────────▶│  origins=[5173]  ③     │
│   "include"      ①    │                 │  supports_credentials  │
│ })                    │ ◀───────────────│         =True     ②    │
│                       │  Set-Cookie受信 │  session["user_id"]    │
└───────────────────────┘                 └────────────────────────┘
```

> 🧠 **考え方**: ブラウザは「別オリジンへ Cookie を無断で送る/受け取る」ことを既定で禁止する（CSRF等の安全のため）。
> だから**送る側(fetch)と受ける側(CORS)の両方で明示的に許可**して初めて往復できる。

> ⏭️ **回収（Step 3 の宣言）**: Step 3 で「`supports_credentials` とフロントの対応は Step 6 で図解」と予告した。上の3点セットがその回収。

---

## 6-2. フロントを作る

```bash
# flaskr-api/ の中で（バックと並べる）
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 🔬 構文解剖: `npm create vite@latest frontend -- --template react-ts`

| 部品 | 意味 |
|---|---|
| `npm create vite@latest` | Vite のプロジェクト作成コマンド |
| `frontend` | 作るディレクトリ名 |
| `--` | 「ここから先は create スクリプトへの引数」の区切り |
| `--template react-ts` | React + TypeScript のテンプレートを使う |

（ここは React 側の道具なので既知のはず。詳細説明は割愛せず、要点＝「React+TS の雛形を `frontend/` に作る」）

---

## 6-3. API クライアントを型付きで書く

**ファイル: `frontend/src/api.ts`（新規・全文）**

```typescript
// バックエンドのベースURL（開発中は :5000）
const BASE = "http://localhost:5000";

// API が返す型（Flask の *_to_dict と対応させる）
export type User = { id: number; username: string };
export type Post = {
  id: number;
  title: string;
  body: string;
  created: string; // ISO 8601 文字列
  author: User;
};

// 共通 fetch。Cookie を必ず往復させる
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include", // ★3点セットの①：Cookie を送る/受ける
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `HTTP ${res.status}`);
  }
  // 204 No Content は body が無いので分岐
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  me: () => request<{ user: User | null }>("/auth/me"),
  register: (username: string, password: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  listPosts: () => request<Post[]>("/posts"),
  createPost: (title: string, body: string) =>
    request<Post>("/posts", {
      method: "POST",
      body: JSON.stringify({ title, body }),
    }),
};
```

### 🔬 構文解剖（境界の要点だけ）: `credentials: "include"`

| 部品 | 意味 |
|---|---|
| `credentials: "include"` | fetch に **Cookie を常に含める**よう指示。既定(`"same-origin"`)では別オリジンにCookieを送らない |

**ここが最頻の詰まりどころ**: これを付け忘れると、`login` の Set-Cookie は受け取れても、次の `/auth/me` に Cookie が乗らず**毎回未ログイン扱い**になる。
**Flask 側との対応**: サーバーの `supports_credentials=True`（②）と**必ずペア**。片方だけでは往復しない。

### 🔬 構文解剖: `res.json().catch(() => ({}))` と `body.error ?? ...`

| 部品 | 意味 |
|---|---|
| `.catch(() => ({}))` | JSON パース失敗時に空オブジェクトで握りつぶす（本文なしエラー応答対策） |
| `body.error ?? ...` | Flask が返す `{"error": "..."}`（Step 3/4 の形）を取り出す。無ければ既定文言 |

**Flask 側との対応**: Step 4 の `errorhandler` が全エラーを `{"error":..,"status":..}` に統一したので、フロントは `body.error` を一律に読める。**サーバーのエラー形式を揃えた恩恵**がここで出る。

---

## 6-4. 画面を作る（最小）

**ファイル: `frontend/src/App.tsx`（全文）**

```tsx
import { useEffect, useState } from "react";
import { api, type Post, type User } from "./api";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState("");

  // 初回：ログイン状態と記事一覧を読む
  useEffect(() => {
    api.me().then((r) => setUser(r.user)).catch(() => {});
    refreshPosts();
  }, []);

  async function refreshPosts() {
    setPosts(await api.listPosts());
  }

  async function handleLogin() {
    setError("");
    try {
      const u = await api.login(username, password);
      setUser(u);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleLogout() {
    await api.logout();
    setUser(null);
  }

  async function handleCreate() {
    setError("");
    try {
      await api.createPost(title, body);
      setTitle("");
      setBody("");
      await refreshPosts();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>Flaskr（React + Flask + MySQL）</h1>

      {error && <p style={{ color: "crimson" }}>エラー: {error}</p>}

      {user ? (
        <section>
          <p>
            こんにちは <b>{user.username}</b> さん{" "}
            <button onClick={handleLogout}>ログアウト</button>
          </p>
          <h2>記事を書く</h2>
          <input placeholder="タイトル" value={title} onChange={(e) => setTitle(e.target.value)} />
          <br />
          <textarea placeholder="本文" value={body} onChange={(e) => setBody(e.target.value)} />
          <br />
          <button onClick={handleCreate}>投稿</button>
        </section>
      ) : (
        <section>
          <h2>ログイン</h2>
          <input placeholder="ユーザー名" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input placeholder="パスワード" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button onClick={handleLogin}>ログイン</button>
          <p style={{ fontSize: 12, color: "#666" }}>
            未登録の場合は先に <code>curl</code> か、api.register を使って登録してください。
          </p>
        </section>
      )}

      <h2>記事一覧</h2>
      <ul>
        {posts.map((p) => (
          <li key={p.id}>
            <b>{p.title}</b> — {p.author.username}（{new Date(p.created).toLocaleString()}）
            <br />
            {p.body}
          </li>
        ))}
      </ul>
    </main>
  );
}
```

（React/TS の文法＝あなたの既知分野なので解剖は省略。`new Date(p.created)` は、Flask が `isoformat()` で返した ISO 文字列を JS の `Date` に戻している点だけ注記＝Step 4 の `created.isoformat()` と対応。）

---

## 6-5. 起動して動作確認

3つを別々に起動します（iTerm2 のタブを分けると楽）。

```bash
# タブ1: MySQL
docker compose up -d

# タブ2: Flask API
uv run flask --app flaskr run --port 5000

# タブ3: React
cd frontend && npm run dev   # http://localhost:5173
```

### 🔮 実行前に予想しよう
1. `credentials:"include"` を**消す**と、ログイン後に画面をリロードしたらログイン状態はどうなる？
2. ブラウザの DevTools → Network で `login` のレスポンスに現れるヘッダは？

<details><summary>答え</summary>

1. リロードで `me()` に Cookie が送られず `user:null` になる＝ログインが維持されない。3点セットの①が欠けるとこうなる。
2. `Set-Cookie: session=...` と、CORS の `Access-Control-Allow-Credentials: true` / `Access-Control-Allow-Origin: http://localhost:5173`。②③がヘッダに出ている。
</details>

### 期待される動作
- ログイン → `user` が入り、投稿フォームが出る
- 投稿 → 一覧が増える
- リロードしてもログイン状態が保たれる（Cookie が往復している証拠）

---

## 6-6. 🏢 実務メモ / ⚠️ アンチパターン

### 🏢 実務メモ
`api.ts` に**型(`User`/`Post`)とfetchを集約**し、画面は `api.xxx()` を呼ぶだけにするのは実務の定番。
型はサーバーの `*_to_dict`（Step 3/4）と手で対応させたが、規模が大きいと **OpenAPI から型を自動生成**する（発展課題）。`BASE` は本番でドメインが変わるので**環境変数(`import.meta.env`)に外出し**する。

### ⚠️ やりがち
> **やりがち**: CORS の `origins` を `"*"`（全許可）にしたまま Cookie を使おうとして、ブラウザに拒否される。
> **現場では**: Cookie（credentials）を伴うときは `origins` に**具体的なオリジン**を列挙する。`*` と credentials は**併用不可**というブラウザ仕様。

---

## 6-7. ✅ 想起チェック

<details><summary>Q1. 別オリジンで Cookie を往復させる「3点セット」は？</summary>

①fetch の `credentials:"include"`、②サーバー CORS の `supports_credentials=True`、③CORS の `origins` に具体的URL（`*` 不可）。全部そろって往復する。
</details>

<details><summary>Q2. `credentials:"include"` を忘れると症状は？</summary>

login はできても Cookie が後続リクエストに乗らず、リロードや `me()` で毎回未ログイン扱いになる。
</details>

<details><summary>Q3. フロントの `Post.created` が `string` 型なのはなぜ？</summary>

Flask が `datetime` を `isoformat()` で ISO 文字列にして返すから（Step 4）。JS 側は `new Date(...)` で日時に戻す。
</details>

---

## ✍️ ブランクページ（章末の再現）

`api.ts` の `request` 関数を白紙から再現。特に:
- `credentials:"include"`
- `Content-Type: application/json`
- `!res.ok` のときサーバーの `error` を読んで throw
- `204` の分岐

---

## まとめ

- 別オリジン + Cookie は**3点セット**（fetch の `credentials` / CORS の `supports_credentials` / 具体的 `origins`）
- API クライアントに**型とfetchを集約**し、画面は呼ぶだけ
- サーバーで**エラー形式を統一**（Step 4）した恩恵がフロントのエラー処理で効く
- 日時は ISO 文字列で往復（`isoformat()` ↔ `new Date()`）

次の [Step 7](./07-wrapup.md) で、つまずき集・まとめ・**宿題（Lv1〜3）**・発展をまとめます。
