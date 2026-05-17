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

    # ---- 行业板块 ----

    def upsert_industry_mapping(self, df: pd.DataFrame):
        """写入股票行业映射"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO industry_mapping SELECT code, industry_name FROM df")

    def get_industry_for_stock(self, code: str) -> str:
        """查询股票所属行业"""
        result = self.conn.execute(
            "SELECT industry_name FROM industry_mapping WHERE code = ?", [code]
        ).fetchone()
        return result[0] if result else ""

    def get_stocks_in_industry(self, industry_name: str) -> pd.DataFrame:
        """查询行业内所有股票"""
        return self.conn.execute(
            "SELECT m.code, s.name, m.industry_name FROM industry_mapping m "
            "LEFT JOIN stock_list s ON m.code = s.code "
            "WHERE m.industry_name = ? ORDER BY m.code",
            [industry_name],
        ).fetchdf()

    def upsert_industry_daily(self, df: pd.DataFrame):
        """写入行业日线"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO industry_daily SELECT * FROM df")

    def get_industry_daily(
        self,
        industry_name: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        sql = "SELECT * FROM industry_daily WHERE industry_name = ?"
        params: list = [industry_name]
        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        sql += " ORDER BY date"
        return self.conn.execute(sql, params).fetchdf()

    def get_all_industry_names(self) -> list[str]:
        """获取所有行业名称"""
        df = self.conn.execute(
            "SELECT DISTINCT industry_name FROM industry_mapping ORDER BY industry_name"
        ).fetchdf()
        return df["industry_name"].tolist() if not df.empty else []

    # ---- 资金流向 ----

    def upsert_fund_flow_daily(self, df: pd.DataFrame):
        """写入市场资金流向"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO fund_flow_daily SELECT * FROM df")

    # ---- AI 研报 ----

    def save_report(
        self,
        report_id: str,
        code: str,
        stock_name: str,
        report_text: str,
        market_context: str = "",
        industry_context: str = "",
        news_context: str = "",
        user_input: str = "",
        skills_used: str = "",
        llm_provider: str = "",
    ):
        self.conn.execute(
            "INSERT OR REPLACE INTO ai_reports VALUES (?,?,?,NOW(),?,?,?,?,?,?,?)",
            [report_id, code, stock_name, report_text,
             market_context, industry_context, news_context,
             user_input, skills_used, llm_provider],
        )

    def get_reports(self, code: str, limit: int = 20) -> pd.DataFrame:
        return self.conn.execute(
            "SELECT * FROM ai_reports WHERE code = ? ORDER BY created_at DESC LIMIT ?",
            [code, limit],
        ).fetchdf()

    def get_report_count(self, code: str) -> int:
        result = self.conn.execute(
            "SELECT COUNT(*) FROM ai_reports WHERE code = ?", [code]
        ).fetchone()
        return result[0] if result else 0

    # ---- 分析技能 ----

    def save_skill(
        self,
        skill_id: str,
        skill_text: str,
        reason: str = "",
        code: str = "",
        industry: str = "",
        source_report_ids: str = "",
    ):
        self.conn.execute(
            "INSERT OR REPLACE INTO agent_skills VALUES (?,?,?,?,?,?,NOW(),TRUE)",
            [skill_id, code, industry, skill_text, reason, source_report_ids],
        )

    def get_active_skills(self, code: str = "", industry: str = "") -> pd.DataFrame:
        return self.conn.execute(
            "SELECT * FROM agent_skills WHERE is_active = TRUE "
            "AND (code = '' OR code = ?) AND (industry = '' OR industry = ?) "
            "ORDER BY created_at",
            [code, industry],
        ).fetchdf()

    def toggle_skill(self, skill_id: str, active: bool):
        self.conn.execute(
            "UPDATE agent_skills SET is_active = ? WHERE id = ?",
            [active, skill_id],
        )

    def delete_skill(self, skill_id: str):
        self.conn.execute("DELETE FROM agent_skills WHERE id = ?", [skill_id])

    # ---- 涨停股池 ----

    def upsert_limit_up_pool(self, df: pd.DataFrame):
        """写入涨停股池（按 date+code 去重）"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO limit_up_pool SELECT * FROM df")

    def get_limit_up_pool(self, date_str: str) -> pd.DataFrame:
        """查询某日涨停股池"""
        return self.conn.execute(
            "SELECT * FROM limit_up_pool WHERE date = ? ORDER BY streak DESC, seal_amount DESC",
            [date_str],
        ).fetchdf()

    def get_limit_up_stats(self, start_date: str, end_date: str) -> pd.DataFrame:
        """查询日期范围内每日涨停统计（用于趋势图）"""
        return self.conn.execute(
            "SELECT date, COUNT(*) as count, AVG(streak) as avg_streak "
            "FROM limit_up_pool WHERE date >= ? AND date <= ? "
            "GROUP BY date ORDER BY date",
            [start_date, end_date],
        ).fetchdf()

    # ---- 炸板股池 ----

    def upsert_limit_up_failed_pool(self, df: pd.DataFrame):
        """写入炸板股池（按 date+code 去重）"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO limit_up_failed_pool SELECT * FROM df")

    def get_limit_up_failed_pool(self, date_str: str) -> pd.DataFrame:
        """查询某日炸板股池"""
        return self.conn.execute(
            "SELECT * FROM limit_up_failed_pool WHERE date = ? ORDER BY failed_count DESC",
            [date_str],
        ).fetchdf()

    # ---- 跌停股池 ----

    def upsert_limit_down_pool(self, df: pd.DataFrame):
        """写入跌停股池（按 date+code 去重）"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO limit_down_pool SELECT * FROM df")

    def get_limit_down_pool(self, date_str: str) -> pd.DataFrame:
        """查询某日跌停股池"""
        return self.conn.execute(
            "SELECT * FROM limit_down_pool WHERE date = ? ORDER BY consecutive DESC",
            [date_str],
        ).fetchdf()

    # ---- 昨日涨停 ----

    def upsert_previous_limit_up_pool(self, df: pd.DataFrame):
        """写入昨日涨停股池（按 date+code 去重）"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO previous_limit_up_pool SELECT * FROM df")

    def get_previous_limit_up_pool(self, date_str: str) -> pd.DataFrame:
        """查询某日昨日涨停股池"""
        return self.conn.execute(
            "SELECT * FROM previous_limit_up_pool WHERE date = ? ORDER BY pct_change DESC",
            [date_str],
        ).fetchdf()

    # ---- 情绪汇总 ----

    def upsert_market_sentiment(self, df: pd.DataFrame):
        """写入每日市场情绪汇总"""
        if df.empty:
            return
        self.conn.execute("INSERT OR REPLACE INTO market_sentiment_daily SELECT * FROM df")

    def get_market_sentiment(self, start_date: str, end_date: str) -> pd.DataFrame:
        """查询日期范围内的市场情绪汇总"""
        return self.conn.execute(
            "SELECT * FROM market_sentiment_daily WHERE date >= ? AND date <= ? ORDER BY date",
            [start_date, end_date],
        ).fetchdf()
