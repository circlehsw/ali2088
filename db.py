from sqlalchemy import create_engine, text
from mysql.connector.constants import ClientFlag
import os
try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass

DB_HOST=os.getenv("DB_HOST","").strip()
DB_PORT=int(os.getenv("DB_PORT","3306"))
DB_USER=os.getenv("DB_USER","").strip()
DB_PASSWORD=os.getenv("DB_PASSWORD","").strip()
DB_NAME=os.getenv("DB_NAME","").strip()
if not all([DB_HOST,DB_USER,DB_PASSWORD,DB_NAME]):
    raise RuntimeError("環境變數未設定完整")

dsn = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

_engine = create_engine(
    dsn,
    connect_args={
        "auth_plugin": "caching_sha2_password",
        "client_flags": [ClientFlag.SSL],
        "ssl_disabled": False,
        "ssl_verify_cert": False,
        "ssl_verify_identity": False,
    },
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)

def get_engine(): return _engine
def query_df(sql, params=None):
    import pandas as pd
    with _engine.connect() as c:
        return pd.read_sql(text(sql) if params else sql, c, params=params)
