import functools

from flask import Blueprint, g, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .models import User, db

# "auth" という名前の Blueprint。URLは全部 /auth から始める
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_logged_in_user():
    """毎リクエストの前に、セッションの user_id から User を復元して g.user に置く。"""
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id is not None else None


def login_required(view):
    """ログイン必須のルートに付けるデコレータ。未ログインなら 401 を返す。"""

    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return {"error": "authentication required"}, 401
        return view(*args, **kwargs)

    return wrapped_view


def user_to_dict(user):
    """User を JSON にできる辞書へ変換する。"""
    return {"id": user.id, "username": user.username}


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return {"error": "username and password are required"}, 400

    exists = db.session.scalar(db.select(User).filter_by(username=username))
    if exists is not None:
        return {"error": "username already taken"}, 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    return user_to_dict(user), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    user = db.session.scalar(db.select(User).filter_by(username=username))
    if user is None or not check_password_hash(user.password_hash, password or ""):
        return {"error": "invalid credentials"}, 401

    session.clear()
    session["user_id"] = user.id
    return user_to_dict(user), 200


@bp.post("/logout")
def logout():
    session.clear()
    return "", 204


@bp.get("/me")
def me():
    if g.user is None:
        return {"user": None}, 200
    return {"user": user_to_dict(g.user)}, 200
