import os

import click
from flask import Flask
from flask_cors import CORS

from .models import db  # ★追加：models.py の db を取り込む


def create_app():
    """Flask アプリを組み立てて返すファクトリ関数。"""
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "dev"
    # ★追加：DB接続先（Docker の MySQL）。Step 0 の docker-compose.yml の値と一致させる
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://flaskr:flaskr@127.0.0.1:3306/flaskr"
    )
    # ★追加：実行SQLをログ出力するか。環境変数 SQL_ECHO=1 のときだけ有効（本番では出さない）
    app.config["SQLALCHEMY_ECHO"] = os.environ.get("SQL_ECHO") == "1"

    db.init_app(app)  # ★追加：db をこのアプリに結び付ける

    # ★追加：React(:5173) から Cookie 付きで叩けるように CORS を許可
    CORS(
        app,
        resources={r"/*": {"origins": ["http://localhost:5173"]}},
        supports_credentials=True,
    )

    # ★追加：auth Blueprint を登録
    from .auth import bp as auth_bp

    app.register_blueprint(auth_bp)

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
