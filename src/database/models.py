# src/database/models.py

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import datetime

# Базовый класс для наших моделей, от которого они будут наследоваться
Base = declarative_base()

class Meme(Base):
    # Название таблицы в базе данных
    __tablename__ = 'memes'

    # Описание колонок (полей) таблицы
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False) # unique=True -> не может быть двух мемов с одинаковой ссылкой
    source = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Meme(id={self.id}, title='{self.title[:30]}...', source='{self.source}')>"

class Reaction(Base):
    __tablename__ = 'reactions'

    id = Column(Integer, primary_key=True)
    dominant_emotion = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Связываем реакцию с мемом (один-ко-многим)
    meme_id = Column(Integer, ForeignKey('memes.id'), nullable=False)
    meme = relationship("Meme")

    def __repr__(self):
        return f"<Reaction(meme_id={self.meme_id}, emotion='{self.dominant_emotion}')>"