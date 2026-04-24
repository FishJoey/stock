"""初始化行业数据 — 拉取行业板块列表、成分股映射、行业历史K线"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

from stock.data.akshare_provider import AKShareProvider
from stock.data.storage import Storage


def main():
    storage = Storage()
    provider = AKShareProvider()
    storage.init_tables()

    # 1. 获取行业板块列表
    logger.info("拉取行业板块列表...")
    try:
        industry_list = provider.get_industry_list()
        logger.info(f"获取到 {len(industry_list)} 个行业板块")
    except Exception as e:
        logger.error(f"获取行业列表失败: {e}")
        return

    # 2. 遍历行业，拉取成分股映射
    logger.info("拉取行业成分股映射...")
    total_mapped = 0
    for _, row in industry_list.iterrows():
        name = row["industry_name"]
        try:
            stocks = provider.get_industry_stocks(name)
            if not stocks.empty:
                storage.upsert_industry_mapping(stocks)
                total_mapped += len(stocks)
                logger.debug(f"  {name}: {len(stocks)} 只成分股")
        except Exception as e:
            logger.warning(f"  {name} 成分股拉取失败: {e}")
        time.sleep(0.5)

    logger.info(f"行业映射完成，共 {total_mapped} 条映射记录")

    # 3. 拉取行业历史K线（取前20个行业）
    logger.info("拉取行业历史K线（前20个行业）...")
    success = 0
    for _, row in industry_list.head(20).iterrows():
        name = row["industry_name"]
        try:
            hist = provider.get_industry_hist(name)
            if not hist.empty:
                storage.upsert_industry_daily(hist)
                logger.debug(f"  {name}: {len(hist)} 条K线")
                success += 1
        except Exception as e:
            logger.warning(f"  {name} K线拉取失败: {e}")
        time.sleep(0.5)

    storage.close()
    logger.info(f"行业数据初始化完成! {len(industry_list)} 个行业, {total_mapped} 条映射, {success} 个行业K线")


if __name__ == "__main__":
    main()
