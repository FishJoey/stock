"""A股市场常量定义"""

from decimal import Decimal

# 交易时间
MORNING_OPEN = "09:30"
MORNING_CLOSE = "11:30"
AFTERNOON_OPEN = "13:00"
AFTERNOON_CLOSE = "15:00"
CALL_AUCTION_START = "09:15"  # 集合竞价开始
CALL_AUCTION_END = "09:25"  # 集合竞价结束
CLOSING_AUCTION_START = "14:57"  # 尾盘集合竞价

# 涨跌停幅度
PRICE_LIMIT_MAIN = Decimal("0.10")  # 主板 10%
PRICE_LIMIT_CHINEXT = Decimal("0.20")  # 创业板 20%
PRICE_LIMIT_STAR = Decimal("0.20")  # 科创板 20%
PRICE_LIMIT_ST = Decimal("0.05")  # ST 股票 5%
PRICE_LIMIT_IPO_CHINEXT = Decimal("0.30")  # 创业板/科创板新股前5日 30% (实际不设限)

# 交易费用
COMMISSION_RATE = Decimal("0.00025")  # 佣金万2.5（双向）
COMMISSION_MIN = Decimal("5.0")  # 最低佣金5元
STAMP_TAX_RATE = Decimal("0.0005")  # 印花税千分之0.5（仅卖出）
TRANSFER_FEE_RATE = Decimal("0.00001")  # 过户费万分之0.1

# T+1 规则
SETTLEMENT_DAYS = 1  # A股 T+1

# 股票代码前缀 -> 市场/板块映射
CODE_PREFIX_MAP = {
    "600": ("SH", "主板"),
    "601": ("SH", "主板"),
    "603": ("SH", "主板"),
    "605": ("SH", "主板"),
    "688": ("SH", "科创板"),
    "689": ("SH", "科创板"),
    "000": ("SZ", "主板"),
    "001": ("SZ", "主板"),
    "002": ("SZ", "中小板"),
    "003": ("SZ", "中小板"),
    "300": ("SZ", "创业板"),
    "301": ("SZ", "创业板"),
}

# 指数代码
INDEX_CODES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50": "sh000688",
    "沪深300": "sh000300",
    "中证500": "sh000905",
    "中证1000": "sh000852",
}

# 常用均线周期
MA_PERIODS = [5, 10, 20, 60, 120, 250]


def get_exchange(code: str) -> str:
    """根据股票代码获取交易所"""
    for prefix, (exchange, _) in CODE_PREFIX_MAP.items():
        if code.startswith(prefix):
            return exchange
    return "UNKNOWN"


def get_board(code: str) -> str:
    """根据股票代码获取板块"""
    for prefix, (_, board) in CODE_PREFIX_MAP.items():
        if code.startswith(prefix):
            return board
    return "未知"


def get_price_limit(code: str) -> Decimal:
    """根据股票代码获取涨跌停幅度"""
    board = get_board(code)
    if board in ("创业板", "科创板"):
        return PRICE_LIMIT_CHINEXT
    return PRICE_LIMIT_MAIN
