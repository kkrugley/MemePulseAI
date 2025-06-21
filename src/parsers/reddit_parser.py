# src/parsers/reddit_parser.py

import os
import sys
import praw
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- ВОТ ГЛАВНОЕ ИСПРАВЛЕНИЕ ---
# Это "объясняет" Python, где искать другие наши файлы (например, models.py)
# Мы добавляем корневую папку проекта в путь поиска модулей
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# --- ЯВНО УКАЗЫВАЕМ ПУТЬ К .ENV ФАЙЛУ ---
load_dotenv(os.path.join(project_root, '.env'))

# Теперь, после настройки пути, можно импортировать как обычно
from src.database.models import Meme

# --- Настройка подключения к БД ---
# Путь к БД теперь строится относительно корневой папки проекта
DB_PATH = os.path.join(project_root, "memes.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# --- Загрузка ключей API ---
load_dotenv(os.path.join(project_root, '.env')) # Указываем путь к .env
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

def fetch_and_save_memes(subreddit_names, limit_per_subreddit=10):
    """
    Получает мемы и СОХРАНЯЕТ их в базу данных.
    """
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
        print("Ошибка: Не найдены ключи API Reddit в .env файле.")
        return

    print("Подключаюсь к Reddit API...")
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            read_only=True # Работаем в режиме "только чтение"
        )
        
        new_memes_count = 0
        for sub_name in subreddit_names:
            try:
                print(f"\n--- Обрабатываю r/{sub_name} ---")
                subreddit = reddit.subreddit(sub_name)
                
                for post in subreddit.hot(limit=limit_per_subreddit * 2):
                    if not post.stickied and post.url.endswith(('jpg', 'jpeg', 'png', 'gif')):
                        existing_meme = session.query(Meme).filter_by(url=post.url).first()
                        
                        if not existing_meme:
                            new_meme = Meme(
                                title=post.title,
                                url=post.url,
                                source=sub_name
                            )
                            session.add(new_meme)
                            new_memes_count += 1
                            print(f"  [+] Добавлен новый мем: {post.title[:50]}...")
                
                # Сохраняем пачкой после каждого сабреддита
                session.commit()

            except Exception as e:
                print(f"Не удалось обработать r/{sub_name}. Ошибка: {e}")

        print(f"\n--- ГОТОВО! Всего добавлено {new_memes_count} новых мемов в базу. ---")

    except Exception as e:
        print(f"Критическая ошибка при подключении к Reddit: {e}")

# Блок для ручного тестирования
if __name__ == "__main__":
    print("Этот скрипт предназначен для импорта, а не для прямого запуска.")
    print("Для запуска парсинга используйте scheduler.py или тестируйте функции отдельно.")
    # # Пример ручного вызова для отладки:
    # test_subreddits = ["memes", "RU_Memes", "Pikabu", "dankmemes", "wholesomememes"]
    # fetch_and_save_memes(test_subreddits, 5)