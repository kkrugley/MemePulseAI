# src/telegram_bot/poster.py

import os
import sys
import asyncio
import pandas as pd
from aiogram import Bot
from sqlalchemy import create_engine, not_
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# --- Настройка путей, чтобы скрипт видел другие модули ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.database.models import Meme, Reaction
from src.recommender.model import MemeRecommender

# Загружаем переменные окружения (.env)
load_dotenv()

# --- Конфигурация ---
DB_PATH = os.path.join(project_root, "memes.db")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("TG_CHANNEL_ID") 

engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)

async def post_best_meme():
    """
    Находит лучший мем и публикует его в Telegram-канал.
    """
    if not all([BOT_TOKEN, CHANNEL_ID]):
        print("Ошибка: BOT_TOKEN или TG_CHANNEL_ID не найдены в .env файле.")
        return

    session = Session()
    bot = Bot(token=BOT_TOKEN)
    
    print("Идет подбор лучшего мема для публикации...")

    # 1. Загружаем обученную модель
    recommender = MemeRecommender()
    recommender.load()

    if not recommender.is_trained:
        print("Модель не обучена. Публикация невозможна.")
        await bot.session.close()
        return

    # 2. Находим все мемы, которые еще не были просмотрены (и не будут опубликованы)
    reacted_meme_ids_query = session.query(Reaction.meme_id).distinct()
    reacted_ids = [id_tuple[0] for id_tuple in reacted_meme_ids_query.all()]
    
    unseen_memes_query = session.query(Meme).filter(not_(Meme.id.in_(reacted_ids)))
    unseen_memes = unseen_memes_query.all()
    
    if not unseen_memes:
        print("Нет непросмотренных мемов для оценки.")
        await bot.session.close()
        return

    # 3. Оцениваем все непросмотренные мемы
    unseen_memes_df = pd.DataFrame([{'id': m.id, 'source': m.source, 'url': m.url, 'title': m.title} for m in unseen_memes])
    scores = recommender.predict_scores(unseen_memes_df)
    unseen_memes_df['score'] = scores
    
    # 4. Находим самый лучший
    best_meme = unseen_memes_df.sort_values(by='score', ascending=False).iloc[0]

    print(f"Выбран лучший мем: '{best_meme['title']}' с оценкой {best_meme['score']:.2f}")

    # 5. Публикуем его в канал == НАСТРОЙКА ВИДА ПУБЛИКАЦИИ (CAPTION) ==
    try:
        caption = f"Источник: r/{best_meme['source']}\n\n<i>Оценка мема моделью: {best_meme['score']}</i>"
        await bot.send_photo(chat_id=CHANNEL_ID, photo=best_meme['url'], caption=caption, parse_mode="HTML")
        print(f"Мем успешно опубликован в канале {CHANNEL_ID}!")

        # 6. Важно! Добавляем "реакцию", чтобы этот мем больше не рассматривался
        # Мы используем фиктивную эмоцию "published"
        published_reaction = Reaction(meme_id=int(best_meme['id']), dominant_emotion="published")
        session.add(published_reaction)
        session.commit()
        print("Мем помечен как опубликованный.")

    except Exception as e:
        print(f"Ошибка при публикации в Telegram: {e}")
    finally:
        # Важно закрыть сессию с Telegram API
        await bot.session.close()
        session.close()

# Блок для ручного тестирования скрипта
if __name__ == "__main__":
    # Для запуска асинхронной функции из синхронного кода
    asyncio.run(post_best_meme())