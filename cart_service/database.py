from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Kết nối MySQL (container tên là 'db', pass là '123456')
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@db/cart_db"

# Lưu ý: Đã xóa connect_args check_same_thread (chỉ dành cho SQLite)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()