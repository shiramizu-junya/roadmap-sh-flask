"""動作確認用のシードデータを投入するスクリプト。

docs/04-blog-api.md の 4-1（一覧・作成・取得）の動作確認用。
アプリ本体（flaskr/）には手を入れず、外から DB に入れるだけの補助スクリプト。

使い方:
    uv run python seed.py            # ユーザーを用意し、記事が0件なら3件入れる
    uv run python seed.py --reset    # 記事を全削除してから3件入れ直す

⚠️ 開発用 DB 専用（docker-compose.yml で起動したローカル MySQL 向け）。
   --reset は posts テーブルを全件 DELETE し、AUTO_INCREMENT を 1 に戻す。
   本番やステージングの DB に向けて実行しないこと。
"""

import sys
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from flaskr import create_app
from flaskr.models import Post, User, db

# docs の動作確認コマンドと同じパスワードに揃える
PASSWORD = "pw12345"

# created をずらして入れる。order_by(Post.created.desc()) の並びが目で確認できる
BASE = datetime(2026, 9, 13, 9, 0, tzinfo=timezone.utc)

SEED_POSTS = [
    # (著者, タイトル, 本文, BASE からの経過分)
    ("alice", "最初の記事", "alice が最初に書いた記事の本文です。", 0),
    ("bob", "bob の記事", "bob が書いた記事。一覧に author が別人で出るか確認用。", 30),
    ("alice", "2番目の記事", "created が一番新しいので一覧の先頭に来るはず。", 60),
]


def get_or_create_user(username):
    """username のユーザーを返す。無ければ作る（パスワードは PASSWORD）。"""
    user = db.session.scalar(db.select(User).filter_by(username=username))
    if user is not None:
        print(f"  user {username!r} は既にあるので再利用（id={user.id}）")
        return user

    user = User(username=username, password_hash=generate_password_hash(PASSWORD))
    db.session.add(user)
    db.session.flush()  # id を確定させる（commit 前に author_id が必要）
    print(f"  user {username!r} を作成（id={user.id}, password={PASSWORD}）")
    return user


def main():
    reset = "--reset" in sys.argv

    app = create_app()
    with app.app_context():
        print("ユーザー:")
        users = {name: get_or_create_user(name) for name in ("alice", "bob")}

        count = db.session.scalar(db.select(db.func.count()).select_from(Post))

        if reset and count:
            for post in db.session.scalars(db.select(Post)):
                db.session.delete(post)
            db.session.flush()
            # id を 1 から振り直す（docs の GET /posts/1 がそのまま使えるように）。
            # 全件削除した直後だけ安全な操作。
            db.session.execute(db.text("ALTER TABLE posts AUTO_INCREMENT = 1"))
            print(f"記事: 既存 {count} 件を削除し、id を 1 から振り直し（--reset）")
            count = 0

        if count:
            print(f"記事: 既に {count} 件あるので投入をスキップ（入れ直すなら --reset）")
        else:
            print("記事:")
            for author, title, body, minutes in SEED_POSTS:
                db.session.add(
                    Post(
                        title=title,
                        body=body,
                        author_id=users[author].id,
                        created=BASE + timedelta(minutes=minutes),
                    )
                )
                print(f"  {title!r} を作成（author={author}）")

        db.session.commit()

        print("\n投入後の一覧（created の降順 = GET /posts と同じ並び）:")
        posts = db.session.scalars(db.select(Post).order_by(Post.created.desc())).all()
        for post in posts:
            print(f"  id={post.id} {post.created.isoformat()} {post.title!r} by {post.author.username}")


if __name__ == "__main__":
    main()
