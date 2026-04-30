"""数据层 — 提供统一的数据源访问"""

from stock.data.provider import DataProvider


def get_provider() -> DataProvider:
    """获取默认数据源（baostock）"""
    from stock.data.baostock_provider import BaostockProvider

    return BaostockProvider()
