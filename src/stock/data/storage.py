"""DuckDB 存储层"""

import duckdb
import pandas as pd

from stock.config import settings
from stock.data.schema import ALL_TABLES


class Storage:
    """DuckDB 数据库操作"""

    def __init__(self, db_path: str | None = None):
        self._path = db_path or str(settings.duckdb_abs_path)
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(self._path)
        return self._conn

    def init_tables(self):
        """创建所有表"""
        for ddl in ALL_TABLES:
            self.conn.execute(ddl)

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---- 股票列表 ----

    def upsert_stock_list(self, df: pd.DataFrame):
        """写入股票列表（全量覆盖）"""
        self.conn.execute("DELETE FROM stock_list")
        self.conn.execute("INSERT INTO stock_list SELECT * FROM df")

    def get_stock_list(self) -> pd.DataFrame:
        return self.conn.execute("SELECT * FROM stock_list ORDER BY code").fetchdf()

    def search_stock(self, keyword: str) -> pd.DataFrame:
        """按代码或名称模糊搜索"""
        return self.conn.execute(
            "SELECT * FROM stock_list WHERE code LIKE ? OR name LIKE ? LIMIT 20",
            [f"%{keyword}%", f"%{keyword}%"],
        ).fetchdf()

    # ---- 日K线 ----

    def upsert_daily_kline(self, df: pd.DataFrame):
        """写入日K线（按 code+date 去重）"""
        if df.empty:
            return
        self.conn.execute("""
            INSERT OR REPLACE INTO daily_kline
            SELECT * FROM df
        """)

    def get_daily_kline(
        self,
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """查询日K线"""
        sql = "SELECT * FROM daily_kline WHERE code = ?"
        params: list = [code]
        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        sql += " ORDER BY date"
        return self.conn.execute(sql, params).fetchdf()

    def get_latest_date(self, code: str) -> str | None:
        """获取某只股票最新的K线日期"""
        result = self.conn.execute(
            "SELECT MAX(date) FROM daily_kline WHERE code = ?", [code]
        ).fetchone()
        if result and result[0]:
            return str(result[0])
        return None

    # ---- 指数 ----

    def upsert_index_daily(self, df: pd.DataFrame):
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO index_daily SELECT * FROM df")

    def get_index_daily(
        self,
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        sql = "SELECT * FROM index_daily WHERE code = ?"
        params: list = [code]
        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        sql += " ORDER BY date"
        return self.conn.execute(sql, params).fetchdf()
