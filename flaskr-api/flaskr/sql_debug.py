import time
from typing import Any

import sqlparse
from sqlalchemy import event
from sqlalchemy.engine import Engine


def enable() -> None:
    """実行された SQL を「整形＋実行時間」でターミナルに表示する（開発時のみ有効化）。"""

    @event.listens_for(Engine, "before_cursor_execute")
    def _before(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        # クエリ開始時刻を積む（ネスト対応でリストに push）
        conn.info.setdefault("_qstart", []).append(time.perf_counter())

    @event.listens_for(Engine, "after_cursor_execute")
    def _after(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        elapsed_ms = (time.perf_counter() - conn.info["_qstart"].pop()) * 1000
        # SQL を複数行に整形（キーワードは大文字に）
        pretty = sqlparse.format(statement, reindent=True, keyword_case="upper")
        # ANSI カラー: シアンの見出し / 黄色のパラメータ
        print(f"\n\033[36m── SQL  ({elapsed_ms:.1f} ms) ──\033[0m")
        print(pretty)
        print(f"\033[33mparams:\033[0m {parameters}\n")
