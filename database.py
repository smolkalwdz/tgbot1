from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Создаем базовый класс для моделей
Base = declarative_base()

# Определяем модель пользователя
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    purchases_count = Column(Integer, default=0)
    total_free_hookahs = Column(Integer, default=0)
    
    # Связь с покупками
    purchases = relationship("Purchase", back_populates="user")

# Определяем модель покупки
class Purchase(Base):
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    purchase_date = Column(DateTime, default=datetime.utcnow)
    is_free = Column(Boolean, default=False)
    qr_code = Column(String)
    verified = Column(Boolean, default=False)
    
    # Связь с пользователем
    user = relationship("User", back_populates="purchases")

# Создаем движок базы данных
engine = create_engine('sqlite:///hookah.db')

# Создаем все таблицы
Base.metadata.create_all(engine)

# Создаем фабрику сессий
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 