# create_db.py

from sqlalchemy import create_engine
from src.database.models import Base

# Имя нашей будущей базы данных
DB_NAME = "memes.db"
# Создаем "движок", который будет работать с файлом нашей БД
engine = create_engine(f"sqlite:///{DB_NAME}")

def setup_database():
    """
    Создает таблицы в базе данных на основе моделей.
    """
    print("Создание таблиц в базе данных...")
    # Base.metadata.create_all() проходит по всем классам, унаследованным от Base,
    # и создает для них таблицы в БД.
    Base.metadata.create_all(engine)
    print(f"База данных '{DB_NAME}' и таблицы успешно созданы.")

if __name__ == "__main__":
    setup_database()