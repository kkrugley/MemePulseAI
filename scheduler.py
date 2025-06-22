# scheduler.py

import time
import os
import sys
import asyncio
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

# --- Настройка путей, чтобы планировщик видел наши скрипты ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Импортируем наши функции. Переименовываем, чтобы избежать конфликтов.
from src.parsers.vk_parser import fetch_and_save_vk_memes
from src.parsers.reddit_parser import fetch_and_save_memes as fetch_and_save_reddit_memes
from src.telegram_bot.poster import post_best_meme

# Загружаем переменные окружения (.env)
load_dotenv()

# --- Конфигурация источников ---
# Русскоязычные
RU_SUBREDDITS = ["Pikabu", "Epicentr", "rus_memes"]
VK_GROUPS = ['memes', '4ch', 'dayvinchik', 'dobriememy', 'anekdot']

# Англоязычные (для разнообразия)
EN_SUBREDDITS = ["memes", 'dankmemes', "wholesomememes", "comics"]

# --- КОЛИЧЕСТВО МЕМОВ ДЛЯ ЗАГРУЗКИ ---
# Вот где теперь настраивается количество для каждой группы источников
COUNT_RU_REDDIT = 25
COUNT_EN_REDDIT = 15
COUNT_VK = 30

# --- Определение задач (Jobs) ---

def run_parsing_job():
    """
    Задача для парсинга новых мемов из ВСЕХ источников.
    """
    print("="*50)
    print(f"[{time.ctime()}] Запускаю плановый парсинг мемов...")
    try:
        # Передаем сюда наши переменные с количеством
        print("\n--- Парсинг русскоязычного Reddit ---")
        fetch_and_save_reddit_memes(RU_SUBREDDITS, limit_per_subreddit=COUNT_RU_REDDIT)
        
        print("\n--- Парсинг VK ---")
        fetch_and_save_vk_memes(VK_GROUPS, count=COUNT_VK)
        
        print("\n--- Парсинг англоязычного Reddit ---")
        fetch_and_save_reddit_memes(EN_SUBREDDITS, limit_per_subreddit=COUNT_EN_REDDIT)

        print(f"\n[{time.ctime()}] Все задачи парсинга успешно завершены.")
    except Exception as e:
        print(f"[{time.ctime()}] Ошибка во время парсинга: {e}")
    print("="*50)


async def run_posting_job():
    """Асинхронная обертка для задачи публикации в Telegram."""
    print("="*50)
    print(f"[{time.ctime()}] Запускаю плановую публикацию лучшего мема...")
    try:
        # Убедимся, что asyncio правильно используется
        await post_best_meme()
        print(f"[{time.ctime()}] Задача публикации завершена.")
    except Exception as e:
        print(f"[{time.ctime()}] Ошибка во время публикации: {e}")
    print("="*50)


# --- Настройка и запуск планировщика ---

if __name__ == "__main__":
    # Создаем экземпляр планировщика
    # Укажи свой часовой пояс, например "Europe/Moscow", "Asia/Yekaterinburg"
    scheduler = BlockingScheduler(timezone="Europe/Moscow") 

    # 1. Задача парсинга: будет запускаться каждые 4 часа.
    scheduler.add_job(run_parsing_job, 'interval', hours=4, id='parsing_job', name="Periodic Meme Parsing")
    print("Задача парсинга настроена: запуск каждые 4 часа.")

    # 2. Задача публикации: будет запускаться каждый день в 20:00.
    scheduler.add_job(run_posting_job, 'cron', hour=20, minute=0, id='posting_job', name="Daily Telegram Post")
    print("Задача публикации настроена: запуск ежедневно в 20:00.")

    print("\nПланировщик готов к запуску. Нажмите Ctrl+C для выхода.")
    
    # Запускаем первую задачу парсинга сразу при старте, не дожидаясь 4 часов
    print("Запускаю первоначальный парсинг...")
    run_parsing_job()

    try:
        # Запускаем основной цикл планировщика
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\nОстанавливаю планировщик...")
        scheduler.shutdown()
        print("Планировщик остановлен.")