from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot.db")
# For cPanel MySQL example: mysql+pymysql://username:password@host:3306/databasename

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_user_id = Column(Integer, unique=True, nullable=True)
    bale_user_id = Column(Integer, unique=True, nullable=True)
    username = Column(String(255))
    first_name = Column(String(255))
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    linked_at = Column(DateTime, nullable=True)
    link_code = Column(String(50), nullable=True)  # برای لینک کردن موقت
    link_code_platform = Column(String(10), nullable=True)  # 'tg' یا 'bale'

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db, tg_id=None, bale_id=None, username=None, first_name=None):
    """دریافت یا ایجاد کاربر بر اساس ID پلتفرم"""
    user = None
    if tg_id:
        user = db.query(User).filter(User.tg_user_id == tg_id).first()
    elif bale_id:
        user = db.query(User).filter(User.bale_user_id == bale_id).first()
    
    if not user:
        user = User(
            tg_user_id=tg_id,
            bale_user_id=bale_id,
            username=username,
            first_name=first_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # آپدیت اطلاعات اگر تغییر کرده
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        db.commit()
    return user