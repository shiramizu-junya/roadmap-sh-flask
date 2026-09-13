from flask import Blueprint, abort, g, request

from .auth import login_required
from .models import Post, db

bp = Blueprint("posts", __name__, url_prefix="/posts")


def post_to_dict(post):
    """Post を JSON 用の辞書へ変換する。"""
    return {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "created": post.created.isoformat(),
        "author": {"id": post.author.id, "username": post.author.username},
    }


def get_post_or_404(post_id):
    """id で1件取得。無ければ 404 で打ち切る。"""
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404, description="post not found")
    return post


@bp.get("")
def index():
    posts = db.session.scalars(db.select(Post).order_by(Post.created.desc())).all()
    return [post_to_dict(p) for p in posts], 200


@bp.post("")
@login_required
def create():

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    body = data.get("body")

    if not title or not body:
        return {"error": "title and body are required"}, 400

    post = Post(title=title, body=body, author_id=g.user.id)
    db.session.add(post)
    db.session.commit()
    return post_to_dict(post), 201


@bp.get("/<int:post_id>")
def show(post_id):
    post = get_post_or_404(post_id)
    return post_to_dict(post), 200
