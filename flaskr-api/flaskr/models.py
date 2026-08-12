from __future__ import annotations

from datetime import UTC, datetime

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 全モデルの共通の親。DeclarativeBase を直接継承すると、型チェッカーが
# コンストラクタ（User(username=...) 等）まで型を効かせられる
class Base(DeclarativeBase):
    pass


# 拡張オブジェクト。model_class に Base を渡して結び付ける
db = SQLAlchemy(model_class=Base)


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ユーザー名は一意・必須（MySQL なので長さ必須。80文字まで）。Mapped[str] = NOT NULL
    username: Mapped[str] = mapped_column(db.String(80), unique=True)
    # ハッシュ化したパスワードを保存（ハッシュは長いので255文字。平文は絶対入れない）
    password: Mapped[str] = mapped_column(db.String(255))

    # 1ユーザーが複数 Post を持つ（1対多）
    posts: Mapped[list[Post]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(db.ForeignKey("user.id"))
    # 作成日時。デフォルトで現在時刻（UTC）を入れる
    created: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    # タイトルも長さ必須（255文字）。本文は長文なので Text 型（長さ指定不要）
    title: Mapped[str] = mapped_column(db.String(255))
    body: Mapped[str] = mapped_column(db.Text, default="")

    # Post 側から著者(User)を辿れるようにする
    author: Mapped[User] = relationship(back_populates="posts")

    def to_dict(self) -> dict:
        """JSON レスポンス用の dict に変換する（Jinja テンプレートの代わり）。"""
        # TODO(2): id / title / body / created(ISO文字列) / author_id / username を返す
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "created": self.created.isoformat(),
            "author_id": self.author_id,
            "username": self.author.username,  # リレーション経由で著者名を取得
        }


@click.command("init-db")
def init_db_command() -> None:
    """既存データを消して、モデルからテーブルを作り直す。"""
    db.drop_all()
    db.create_all()
    click.echo("Initialized the database.")


def init_app(app: Flask) -> None:
    # 拡張をこのアプリに結び付ける
    db.init_app(app)
    # `flask init-db` を使えるように登録
    app.cli.add_command(init_db_command)
