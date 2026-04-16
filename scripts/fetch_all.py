"""批量拉取历史数据"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

from stock.config import settings
from stock.data.akshare_provider import AKShareProvider
from stock.data.storage import Storage


def fetch_daily_klines(codes: list[str] | None = None, limit: int = 0):
    """批量拉取日K线数据

    Args:
        codes: 指定股票代码列表，为空则拉取全部
        limit: 限制拉取数量，0 表示不限制
    """
    storage = Storage()
    provider = AKShareProvider()
    storage.init_tables()

    if not codes:
        stock_list = storage.get_stock_list()
        if stock_list.empty:
            logger.error("股票列表为空，请先运行 init_db.py")
            return
        codes = stock_list["code"].tolist()

    if limit > 0:
        codes = codes[:limit]

    total = len(codes)
    logger.info(f"开始拉取 {total} 只股票的日K线数据...")

    success = 0
    for i, code in enumerate(codes, 1):
        try:
            # 增量更新：从最新日期之后开始拉取
            latest = storage.get_latest_date(code)
            start_date = latest if latest else settings.data_start_date

            df = provider.get_daily_kline(code, start_date=start_date)
            if not df.empty:
                storage.upsert_daily_kline(df)
                success += 1

            if i % 50 == 0:
                logger.info(f"进度: {i}/{total} ({success} 成功)")

            time.sleep(0.3)  # 避免请求过快
        except Exception as e:
            logger.warning(f"[{i}/{total}] {code} 失败: {e}")

    storage.close()
    logger.info(f"完成: {success}/{total} 只股票数据拉取成功")


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    fetch_daily_klines(limit=limit)


if __name__ == "__main__":
    main()
