import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_USER = os.getenv("DB_ROOT_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "123456")

# Mặc định trỏ về 'db'
DB_HOST = os.getenv("ORDER_DB_HOST", "db")
DB_NAME = "order_db"

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()