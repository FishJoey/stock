"""定时数据拉取调度器

使用 APScheduler 自动执行：
- 日K线增量拉取（周一至周五 16:00）
- 股票列表更新（每周一 09:00）
- 行业映射更新（每月1号 09:00）

启动: .venv/bin/python3 scripts/scheduler.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger


def job_fetch_klines():
    """日K线增量拉取"""
    logger.info("=== 开始日K线增量拉取 ===")
    try:
        from fetch_all import fetch_daily_klines
        fetch_daily_klines()
        logger.info("=== 日K线拉取完成 ===")
    except Exception as e:
        logger.error(f"日K线拉取失败: {e}")


def job_refresh_stock_list():
    """更新股票列表"""
    logger.info("=== 开始更新股票列表 ===")
    try:
        from init_db import refresh_stock_list
        count = refresh_stock_list()
        logger.info(f"=== 股票列表更新完成: {count} 只 ===")
    except Exception as e:
        logger.error(f"股票列表更新失败: {e}")


def job_refresh_industry():
    """更新行业映射"""
    logger.info("=== 开始更新行业映射 ===")
    try:
        from init_industry import main as init_industry_main
        init_industry_main()
        logger.info("=== 行业映射更新完成 ===")
    except Exception as e:
        logger.error(f"行业映射更新失败: {e}")


def main():
    scheduler = BlockingScheduler()

    scheduler.add_job(
        job_fetch_klines,
        "cron",
        day_of_week="mon-fri",
        hour=16,
        minute=0,
        id="daily_klines",
        name="日K线增量拉取",
    )

    scheduler.add_job(
        job_refresh_stock_list,
        "cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="stock_list",
        name="股票列表更新",
    )

    scheduler.add_job(
        job_refresh_industry,
        "cron",
        day=1,
        hour=9,
        minute=0,
        id="industry_mapping",
        name="行业映射更新",
    )

    logger.info("调度器已启动，按 Ctrl+C 退出")
    logger.info("调度计划:")
    logger.info("  - 日K线增量拉取: 周一至周五 16:00")
    logger.info("  - 股票列表更新:  每周一 09:00")
    logger.info("  - 行业映射更新:  每月1号 09:00")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("调度器已停止")


if __name__ == "__main__":
    main()
