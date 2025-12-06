import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Đọc cấu hình từ biến môi trường
DB_USER = os.getenv("DB_ROOT_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "123456")

# QUAN TRỌNG: Mặc định trỏ về host 'db' (khớp với docker-compose.yml)
DB_HOST = os.getenv("USER_DB_HOST", "db") 
DB_NAME = "user_db"

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()