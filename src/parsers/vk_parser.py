# src/parsers/vk_parser.py 

import os
import sys
import requests
from dotenv import load_dotenv
import vk_api
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- Настройка путей ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# --- ЯВНО УКАЗЫВАЕМ ПУТЬ К .ENV ФАЙЛУ ---
load_dotenv(os.path.join(project_root, '.env'))

# Создаем путь к папке для сохранения изображений
IMAGES_DIR = os.path.join(project_root, 'static', 'images')
os.makedirs(IMAGES_DIR, exist_ok=True) # Создаем папку, если ее нет

from src.database.models import Meme

# --- Конфигурация ---
DB_PATH = os.path.join(project_root, "memes.db")
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")

engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)

def fetch_and_save_vk_memes(group_ids, count=20):
    if not VK_ACCESS_TOKEN:
        print("Ошибка: VK_ACCESS_TOKEN не найден в .env файле.")
        return

    session = Session()
    vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
    vk = vk_session.get_api()
    
    new_memes_count = 0
    print("\n--- Начинаю парсинг и скачивание из VK ---")
    for group_id in group_ids:
        try:
            owner_id = f"-{vk.groups.getById(group_id=group_id)[0]['id']}"
            print(f"Обрабатываю группу: {group_id}")
            wall = vk.wall.get(owner_id=owner_id, count=count)

            for post in wall['items']:
                if 'attachments' in post:
                    for att in post['attachments']:
                        if att['type'] == 'photo':
                            photo = max(att['photo']['sizes'], key=lambda size: size['width'])
                            photo_url = photo['url']
                            
                            # Генерируем уникальное имя файла
                            file_name = f"vk_{post['id']}_{att['photo']['id']}.jpg"
                            local_path = os.path.join(IMAGES_DIR, file_name)
                            
                            # Проверяем, не скачивали ли мы уже этот файл
                            # И нет ли его в базе (по локальному пути)
                            if not os.path.exists(local_path) and not session.query(Meme).filter_by(url=file_name).first():
                                
                                # --- ЛОГИКА СКАЧИВАНИЯ ---
                                try:
                                    response = requests.get(photo_url, stream=True)
                                    response.raise_for_status() # Проверяем, что запрос успешный
                                    with open(local_path, 'wb') as f:
                                        for chunk in response.iter_content(1024):
                                            f.write(chunk)
                                    
                                    # Сохраняем в БД ЛОКАЛЬНЫЙ ПУТЬ
                                    title = post['text'][:250] if post['text'] else f"Мем из {group_id}"
                                    new_meme = Meme(
                                        title=title,
                                        url=file_name, # <-- СОХРАНЯЕМ ИМЯ ФАЙЛА, А НЕ URL
                                        source=f"vk/{group_id}"
                                    )
                                    session.add(new_meme)
                                    new_memes_count += 1
                                    print(f"  [+] Скачан и сохранен мем: {file_name}")

                                except requests.exceptions.RequestException as e:
                                    print(f"    - Ошибка скачивания {photo_url}: {e}")

                            # Берем только первую картинку и идем дальше
                            break
            
            session.commit()
        except Exception as e:
            print(f"Ошибка при обработке группы {group_id}: {e}")

    print(f"--- Парсинг VK завершен. Скачано {new_memes_count} новых мемов. ---")
    session.close()

# Блок для ручного тестирования
if __name__ == "__main__":
    print("Этот скрипт предназначен для импорта, а не для прямого запуска.")
    print("Для запуска парсинга используйте scheduler.py или тестируйте функции отдельно.")
    # # Пример ручного вызова для отладки:
    # test_subreddits = ['memes', '4ch', 'dayvinchik', 'dobriememy', 'anekdot']
    # fetch_and_save_memes(test_subreddits, 5)