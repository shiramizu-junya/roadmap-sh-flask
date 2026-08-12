import os

from flask import Flask


def create_app(test_config: dict | None = None) -> Flask:
    # アプリ本体を生成・設定する「ファクトリ関数」
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # セッション Cookie の署名に使う秘密鍵。.env から読み、無ければ 'dev'
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        # DB 接続先。.env の DATABASE_URL を読む（MySQL に接続する）
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
    )

    if test_config is not None:
        # テスト起動時: 引数で渡された設定で上書き（Step5 で使う）
        app.config.from_mapping(test_config)

    # instance フォルダ（任意の追加設定などを置ける場所）が無ければ作る
    os.makedirs(app.instance_path, exist_ok=True)

    # デバッグ起動時（--debug）だけ、SQL 整形ログを有効化する（Step 0.5 で用意した仕組み）
    if app.debug:
        from . import sql_debug

        sql_debug.enable()

    # 動作確認用の最小ルート
    @app.route("/hello")
    def hello() -> str:
        return "Hello, World!"

    from . import models

    models.init_app(app)

    return app
