import functools
from collections.abc import Callable
from typing import Any

from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .models import User, db

# 'auth' Blueprint。すべての URL に /auth が前置される
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user() -> None:
    """全リクエストの前に走り、ログイン中ユーザーを g.user に載せる。"""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get(User, user_id)


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """未ログインなら 401 を返すデコレータ（Step4 の記事操作で使う）。"""

    @functools.wraps(view)
    def wrapped_view(**kwargs: Any) -> Any:
        # TODO(1): g.user が None なら {"error": "Login required."} を 401 で返す
        ...
        return view(**kwargs)

    return wrapped_view


# ---- 手本: 登録（この形をまねて login/logout/me を書く）----
@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username:
        return jsonify(error="Username is required."), 400
    if not password:
        return jsonify(error="Password is required."), 400
    if db.session.scalar(db.select(User).filter_by(username=username)) is not None:
        return jsonify(error=f"User {username} is already registered."), 400

    user = User(username=username, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify(id=user.id, username=user.username), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    user = db.session.scalar(db.select(User).filter_by(username=username))
    # TODO(2): user が None なら "Incorrect username." を 400 で返す
    # TODO(3): check_password_hash(user.password, password) が False なら
    #          "Incorrect password." を 400 で返す
    ...

    # 認証成功: セッションを作り直して user_id を保存する
    session.clear()
    session["user_id"] = user.id
    return jsonify(id=user.id, username=user.username)


@bp.post("/logout")
def logout():
    # TODO(4): セッションを空にして、本文なし・ステータス 204 を返す
    ...


@bp.get("/me")
def me():
    # TODO(5): g.user が None なら {"user": None}、
    #          いれば {"id":..., "username":...} を返す
    ...
