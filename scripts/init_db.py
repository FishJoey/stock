"""初始化数据库并拉取基础数据"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

from stock.data import get_provider
from stock.data.storage import Storage


def refresh_stock_list():
    """拉取并更新A股股票列表（供 scheduler 复用）"""
    storage = Storage()
    provider = get_provider()
    storage.init_tables()

    logger.info("拉取A股股票列表...")
    stock_list = provider.get_stock_list()
    storage.upsert_stock_list(stock_list)
    logger.info(f"已写入 {len(stock_list)} 只股票")
    storage.close()
    return len(stock_list)


def main():
    storage = Storage()
    provider = get_provider()

    # 1. 创建表
    logger.info("初始化数据库表...")
    storage.init_tables()

    # 2. 拉取股票列表
    logger.info("拉取A股股票列表...")
    stock_list = provider.get_stock_list()
    storage.upsert_stock_list(stock_list)
    logger.info(f"已写入 {len(stock_list)} 只股票")

    # 3. 拉取几只示例股票的日K线
    demo_codes = ["600519", "300750", "000858", "601318"]
    success = 0
    for code in demo_codes:
        logger.info(f"拉取 {code} 日K线...")
        try:
            df = provider.get_daily_kline(code, adjust="qfq")
            if not df.empty:
                storage.upsert_daily_kline(df)
                logger.info(f"  {code} 写入 {len(df)} 条记录")
                success += 1
        except Exception as e:
            logger.warning(f"  {code} 拉取失败: {e}")
        time.sleep(1)  # 请求间隔，避免限流

    storage.close()
    logger.info(f"初始化完成! 股票列表 {len(stock_list)} 只，K线数据 {success}/{len(demo_codes)} 只成功")


if __name__ == "__main__":
    main()
