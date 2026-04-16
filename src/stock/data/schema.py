"""DuckDB 表定义"""

# 股票列表表
CREATE_STOCK_LIST = """
CREATE TABLE IF NOT EXISTS stock_list (
    code VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    exchange VARCHAR,
    board VARCHAR,
    industry VARCHAR,
    list_date VARCHAR
)
"""

# 日K线表
CREATE_DAILY_KLINE = """
CREATE TABLE IF NOT EXISTS daily_kline (
    code VARCHAR NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    amount DOUBLE,
    turnover DOUBLE,
    amplitude DOUBLE,
    pct_change DOUBLE,
    change DOUBLE,
    PRIMARY KEY (code, date)
)
"""

# 指数日K线表
CREATE_INDEX_DAILY = """
CREATE TABLE IF NOT EXISTS index_daily (
    code VARCHAR NOT NULL,
    date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    amount DOUBLE,
    PRIMARY KEY (code, date)
)
"""

ALL_TABLES = [CREATE_STOCK_LIST, CREATE_DAILY_KLINE, CREATE_INDEX_DAILY]
