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

# AI 研报历史
CREATE_AI_REPORTS = """
CREATE TABLE IF NOT EXISTS ai_reports (
    id VARCHAR PRIMARY KEY,
    code VARCHAR NOT NULL,
    stock_name VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    report_text TEXT NOT NULL,
    market_context TEXT DEFAULT '',
    industry_context TEXT DEFAULT '',
    news_context TEXT DEFAULT '',
    user_input TEXT DEFAULT '',
    skills_used TEXT DEFAULT '',
    llm_provider VARCHAR DEFAULT ''
)
"""

# 分析技能（agent 提炼的规则）
CREATE_AGENT_SKILLS = """
CREATE TABLE IF NOT EXISTS agent_skills (
    id VARCHAR PRIMARY KEY,
    code VARCHAR DEFAULT '',
    industry VARCHAR DEFAULT '',
    skill_text TEXT NOT NULL,
    reason TEXT DEFAULT '',
    source_report_ids TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
)
"""

# 涨停股池
CREATE_LIMIT_UP_POOL = """
CREATE TABLE IF NOT EXISTS limit_up_pool (
    date DATE NOT NULL,
    code VARCHAR NOT NULL,
    name VARCHAR,
    pct_change DOUBLE,
    price DOUBLE,
    amount DOUBLE,
    float_mv DOUBLE,
    turnover DOUBLE,
    seal_amount DOUBLE,
    first_seal_time VARCHAR,
    last_seal_time VARCHAR,
    failed_count INTEGER,
    streak INTEGER,
    industry VARCHAR,
    PRIMARY KEY (date, code)
)
"""

# 炸板股池
CREATE_LIMIT_UP_FAILED_POOL = """
CREATE TABLE IF NOT EXISTS limit_up_failed_pool (
    date DATE NOT NULL,
    code VARCHAR NOT NULL,
    name VARCHAR,
    pct_change DOUBLE,
    price DOUBLE,
    limit_price DOUBLE,
    amount DOUBLE,
    float_mv DOUBLE,
    turnover DOUBLE,
    first_seal_time VARCHAR,
    failed_count INTEGER,
    amplitude DOUBLE,
    industry VARCHAR,
    PRIMARY KEY (date, code)
)
"""

# 跌停股池
CREATE_LIMIT_DOWN_POOL = """
CREATE TABLE IF NOT EXISTS limit_down_pool (
    date DATE NOT NULL,
    code VARCHAR NOT NULL,
    name VARCHAR,
    pct_change DOUBLE,
    price DOUBLE,
    amount DOUBLE,
    float_mv DOUBLE,
    turnover DOUBLE,
    seal_amount DOUBLE,
    consecutive INTEGER,
    open_count INTEGER,
    industry VARCHAR,
    PRIMARY KEY (date, code)
)
"""

# 昨日涨停股池（今日表现）
CREATE_PREVIOUS_LIMIT_UP_POOL = """
CREATE TABLE IF NOT EXISTS previous_limit_up_pool (
    date DATE NOT NULL,
    code VARCHAR NOT NULL,
    name VARCHAR,
    pct_change DOUBLE,
    price DOUBLE,
    limit_price DOUBLE,
    amount DOUBLE,
    float_mv DOUBLE,
    turnover DOUBLE,
    amplitude DOUBLE,
    prev_seal_time VARCHAR,
    prev_streak INTEGER,
    industry VARCHAR,
    PRIMARY KEY (date, code)
)
"""

# 每日市场情绪汇总（一天一行）
CREATE_MARKET_SENTIMENT_DAILY = """
CREATE TABLE IF NOT EXISTS market_sentiment_daily (
    date DATE PRIMARY KEY,
    limit_up_count INTEGER,
    limit_up_failed_count INTEGER,
    limit_down_count INTEGER,
    seal_rate DOUBLE,
    promote_rate DOUBLE,
    avg_streak DOUBLE,
    top_industry VARCHAR
)
"""

ALL_TABLES = [
    CREATE_STOCK_LIST, CREATE_DAILY_KLINE, CREATE_INDEX_DAILY,
    CREATE_INDUSTRY_MAPPING, CREATE_INDUSTRY_DAILY, CREATE_FUND_FLOW_DAILY,
    CREATE_AI_REPORTS, CREATE_AGENT_SKILLS, CREATE_LIMIT_UP_POOL,
    CREATE_LIMIT_UP_FAILED_POOL, CREATE_LIMIT_DOWN_POOL,
    CREATE_PREVIOUS_LIMIT_UP_POOL, CREATE_MARKET_SENTIMENT_DAILY,
]
