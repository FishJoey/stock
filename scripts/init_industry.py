"""初始化行业数据 — 拉取行业板块列表和成分股映射"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

from stock.data import get_provider
from stock.data.storage import Storage


def main():
    storage = Storage()
    provider = get_provider()
    storage.init_tables()

    # 1. 获取行业板块列表
    logger.info("拉取行业板块列表...")
    try:
        industry_list = provider.get_industry_list()
        logger.info(f"获取到 {len(industry_list)} 个行业板块")
    except Exception as e:
        logger.error(f"获取行业列表失败: {e}")
        return

    # 2. 批量获取所有股票的行业映射（baostock 一次返回全部）
    logger.info("拉取行业成分股映射...")
    try:
        mappings = provider.get_all_industry_mappings()
        if not mappings.empty:
            storage.upsert_industry_mapping(mappings)
            logger.info(f"行业映射完成，共 {len(mappings)} 条映射记录")
        else:
            logger.warning("未获取到行业映射数据")
    except Exception as e:
        logger.error(f"获取行业映射失败: {e}")

    # 3. 行业历史K线（baostock 不支持，跳过）
    try:
        hist = provider.get_industry_hist("test")
        if hist.empty:
            logger.info("当前数据源不支持行业历史K线，跳过")
    except NotImplementedError:
        logger.info("当前数据源不支持行业历史K线，跳过")

    storage.close()
    logger.info(f"行业数据初始化完成! {len(industry_list)} 个行业")


if __name__ == "__main__":
    main()
