"""配置管理"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，支持 .env 文件和环境变量"""

    # 数据库
    duckdb_path: str = "data/duckdb/stock.duckdb"

    # Tushare（可选）
    tushare_token: str = ""

    # 数据
    data_start_date: str = "20220101"  # 默认拉取起始日期

    # 日志
    log_level: str = "INFO"

    # Web
    streamlit_port: int = 8501

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def duckdb_abs_path(self) -> Path:
        """返回 DuckDB 绝对路径"""
        p = Path(self.duckdb_path)
        if not p.is_absolute():
            p = Path(__file__).parent.parent.parent / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
