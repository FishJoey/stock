"""Baostock 数据适配器 — 替代东财 push2 系列接口"""

from datetime import date, timedelta

import baostock as bs
import pandas as pd
from loguru import logger

from stock.constants import get_board, get_exchange
from stock.data.provider import DataProvider


class BaostockProvider(DataProvider):
    """基于 baostock 的免费数据源（日K线、指数、行业分类）

    baostock 不提供：行业指数K线、资金流向数据。
    这些方法继承基类默认实现（返回空 DataFrame）。
    """

    def __init__(self):
        self._logged_in = False
        self._industry_cache: pd.DataFrame | None = None

    # ---- 会话管理 ----

    def _ensure_login(self):
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != "0":
                raise RuntimeError(f"baostock login failed: {lg.error_msg}")
            self._logged_in = True

    def logout(self):
        if self._logged_in:
            bs.logout()
            self._logged_in = False
            self._industry_cache = None

    def __del__(self):
        try:
            self.logout()
        except Exception:
            pass

    def __enter__(self):
        self._ensure_login()
        return self

    def __exit__(self, *args):
        self.logout()

    # ---- 辅助方法 ----

    @staticmethod
    def _to_bs_code(code: str) -> str:
        """'600519' -> 'sh.600519', '000858' -> 'sz.000858'"""
        exchange = get_exchange(code)
        prefix = "sh" if exchange == "SH" else "sz"
        return f"{prefix}.{code}"

    @staticmethod
    def _index_to_bs_code(code: str) -> str:
        """'sh000001' -> 'sh.000001'"""
        return f"{code[:2]}.{code[2:]}"

    @staticmethod
    def _to_date_str(d: str | date | None, default: str) -> str:
        """统一转为 YYYY-MM-DD 格式（baostock 要求）"""
        if d is None:
            return default
        if isinstance(d, date):
            return d.strftime("%Y-%m-%d")
        s = d.replace("-", "")
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        return d

    # ---- 核心接口 ----

    def get_stock_list(self) -> pd.DataFrame:
        """获取全部A股股票列表"""
        self._ensure_login()
        logger.info("正在从 baostock 获取股票列表...")

        # 尝试今天，非交易日则往前找
        for offset in range(7):
            day = (date.today() - timedelta(days=offset)).strftime("%Y-%m-%d")
            rs = bs.query_all_stock(day=day)
            df = rs.get_data()
            if not df.empty:
                break
        else:
            logger.error("无法获取股票列表（最近7天均无数据）")
            return pd.DataFrame()

        # 过滤A股
        mask = df["code"].str.match(r"^(sh\.6|sz\.0|sz\.3)")
        df = df[mask].copy()

        result = pd.DataFrame({
            "code": df["code"].str.split(".").str[1],
            "name": df["code_name"],
        })
        result["exchange"] = result["code"].apply(get_exchange)
        result["board"] = result["code"].apply(get_board)
        result["industry"] = ""
        result["list_date"] = ""
        result = result[result["name"].str.strip() != ""].reset_index(drop=True)
        logger.info(f"获取到 {len(result)} 只股票")
        return result

    def get_daily_kline(
        self,
        code: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取日K线数据"""
        self._ensure_login()
        bs_code = self._to_bs_code(code)
        start_str = self._to_date_str(start_date, "2020-01-01")
        end_str = self._to_date_str(end_date, date.today().strftime("%Y-%m-%d"))

        adjust_map = {"": "3", "qfq": "2", "hfq": "1"}
        bs_adjust = adjust_map.get(adjust, "3")

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,preclose,volume,amount,turn,pctChg",
            start_date=start_str, end_date=end_str,
            frequency="d", adjustflag=bs_adjust,
        )
        df = rs.get_data()
        if df.empty:
            return pd.DataFrame()

        for col in ["open", "high", "low", "close", "preclose",
                     "volume", "amount", "turn", "pctChg"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        preclose = df["preclose"]
        result = pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["date"]).dt.date,
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "close": df["close"],
            "volume": df["volume"],
            "amount": df["amount"],
            "turnover": df["turn"].fillna(0),
            "amplitude": ((df["high"] - df["low"]) / preclose * 100).fillna(0),
            "pct_change": df["pctChg"].fillna(0),
            "change": (df["close"] - preclose).fillna(0),
        })
        return result.reset_index(drop=True)

    def get_index_daily(
        self,
        code: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
    ) -> pd.DataFrame:
        """获取指数日K线"""
        self._ensure_login()
        bs_code = self._index_to_bs_code(code)
        start_str = self._to_date_str(start_date, "2020-01-01")
        end_str = self._to_date_str(end_date, date.today().strftime("%Y-%m-%d"))

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume,amount",
            start_date=start_str, end_date=end_str,
            frequency="d",
        )
        df = rs.get_data()
        if df.empty:
            return pd.DataFrame()

        for col in ["open", "high", "low", "close", "volume", "amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["date"]).dt.date,
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "close": df["close"],
            "volume": df["volume"].fillna(0),
            "amount": df["amount"].fillna(0),
        })

    # ---- 行业板块（CSRC 证监会分类）----

    def _load_industry_cache(self) -> pd.DataFrame:
        if self._industry_cache is not None:
            return self._industry_cache
        self._ensure_login()
        rs = bs.query_stock_industry()
        self._industry_cache = rs.get_data()
        return self._industry_cache

    def get_industry_list(self) -> pd.DataFrame:
        """获取行业板块列表（CSRC 证监会分类）"""
        df = self._load_industry_cache()
        if df.empty:
            return pd.DataFrame()

        industries = df["industry"].dropna()
        industries = industries[industries.str.strip() != ""].unique()

        return pd.DataFrame({
            "industry_name": industries,
            "board_code": "",
            "pct_change": 0.0,
            "turnover": 0.0,
            "amount": 0.0,
            "leading_stock": "",
        })

    def get_industry_stocks(self, industry_name: str) -> pd.DataFrame:
        """获取行业成分股"""
        df = self._load_industry_cache()
        if df.empty:
            return pd.DataFrame()

        filtered = df[df["industry"] == industry_name]
        if filtered.empty:
            return pd.DataFrame()

        return pd.DataFrame({
            "code": filtered["code"].str.split(".").str[1],
            "name": filtered["code_name"],
            "industry_name": industry_name,
        }).reset_index(drop=True)

    def get_all_industry_mappings(self) -> pd.DataFrame:
        """批量获取所有股票的行业映射"""
        df = self._load_industry_cache()
        if df.empty:
            return pd.DataFrame()

        valid = df[df["industry"].str.strip() != ""].copy()
        return pd.DataFrame({
            "code": valid["code"].str.split(".").str[1],
            "name": valid["code_name"],
            "industry_name": valid["industry"],
        }).reset_index(drop=True)

    # ---- 资金流向（委托 akshare datacenter 接口）----

    def get_north_fund_flow(self) -> pd.DataFrame:
        """获取北向资金（沪深港通）"""
        try:
            from stock.data.akshare_provider import AKShareProvider
            return AKShareProvider().get_north_fund_flow()
        except Exception as e:
            logger.warning(f"北向资金获取失败: {e}")
            return pd.DataFrame()

    def get_stock_fund_flow(self, code: str) -> pd.DataFrame:
        """获取个股资金流向（委托 AKShare）"""
        try:
            from stock.data.akshare_provider import AKShareProvider
            return AKShareProvider().get_stock_fund_flow(code)
        except Exception as e:
            logger.warning(f"个股资金流向获取失败: {e}")
            return pd.DataFrame()

    def get_financial_indicator(self, code: str) -> pd.DataFrame:
        """获取个股财务指标（委托 AKShare）"""
        try:
            from stock.data.akshare_provider import AKShareProvider
            return AKShareProvider().get_financial_indicator(code)
        except Exception as e:
            logger.warning(f"财务指标获取失败: {e}")
            return pd.DataFrame()
