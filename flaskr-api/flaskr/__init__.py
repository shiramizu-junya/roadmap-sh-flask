import click
from flask import Flask

from .models import db  # ★追加：models.py の db を取り込む


def create_app():
    """Flask アプリを組み立てて返すファクトリ関数。"""
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "dev"
    # ★追加：DB接続先（Docker の MySQL）。Step 0 の docker-compose.yml の値と一致させる
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr"
    )

    db.init_app(app)  # ★追加：db をこのアプリに結び付ける

    @app.cli.command("init-db")
    def init_db():
        """モデル定義から全テーブルを作成する。"""
        with app.app_context():
            db.create_all()
        click.echo("初期化しました")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
