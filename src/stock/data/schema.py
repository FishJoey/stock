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

# 行业板块映射表（股票 → 行业）
CREATE_INDUSTRY_MAPPING = """
CREATE TABLE IF NOT EXISTS industry_mapping (
    code VARCHAR NOT NULL,
    industry_name VARCHAR NOT NULL,
    PRIMARY KEY (code)
)
"""

# 行业板块日线
CREATE_INDUSTRY_DAILY = """
CREATE TABLE IF NOT EXISTS industry_daily (
    industry_name VARCHAR NOT NULL,
    date DATE NOT NULL,
    close DOUBLE,
    pct_change DOUBLE,
    turnover DOUBLE,
    amount DOUBLE,
    PRIMARY KEY (industry_name, date)
)
"""

# 市场资金流向（北向 + 两融 + 大盘资金）
CREATE_FUND_FLOW_DAILY = """
CREATE TABLE IF NOT EXISTS fund_flow_daily (
    date DATE PRIMARY KEY,
    north_net DOUBLE,
    margin_balance DOUBLE,
    main_net DOUBLE,
    super_large_net DOUBLE,
    large_net DOUBLE,
    medium_net DOUBLE,
    small_net DOUBLE
)
"""

ALL_TABLES = [
    CREATE_STOCK_LIST, CREATE_DAILY_KLINE, CREATE_INDEX_DAILY,
    CREATE_INDUSTRY_MAPPING, CREATE_INDUSTRY_DAILY, CREATE_FUND_FLOW_DAILY,
]
