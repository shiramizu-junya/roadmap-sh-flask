from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 型情報を持つ基底クラス（SQLAlchemy 2.0 スタイル）
class Base(DeclarativeBase):
    pass


# DB拡張のインスタンス。まだアプリには結び付いていない（後で init_app で結ぶ）
db = SQLAlchemy(model_class=Base)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # このユーザーが書いた記事たち（1対多のリレーション）
    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(db.Model):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="posts")
