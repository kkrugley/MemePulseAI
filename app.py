# app.py

import os
import random
import base64
import numpy as np
import cv2
import logging
import pandas as pd

from flask import Flask, render_template, g, request, jsonify
from sqlalchemy import create_engine, not_
from sqlalchemy.orm import sessionmaker
from deepface import DeepFace

# Абсолютные импорты, которые работают всегда
from src.database.models import Meme, Reaction
from src.recommender.model import MemeRecommender

# --- Настройка приложения ---
app = Flask(__name__)
DB_NAME = "memes.db"
DATABASE_URL = f"sqlite:///{DB_NAME}"

# Отключаем лишние логи от deepface
logging.getLogger('deepface').setLevel(logging.ERROR)

# Настройка подключения к БД
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# --- Инициализация модели ---
recommender = MemeRecommender()
recommender.load()

# --- Рейтинг эмоций ---
EMOTION_PRIORITY = {
    'happy': 5,
    'surprise': 4,
    'neutral': 3,
    'fear': 2,
    'sad': 2,
    'disgust': 1,
    'angry': 1,
    'лицо не найдено': 0,
    'ошибка анализа': 0
}

# --- Управление сессиями БД ---
def get_db_session():
    if 'db_session' not in g:
        g.db_session = Session()
    return g.db_session

@app.teardown_appcontext
def close_db_session(exception=None):
    db_session = g.pop('db_session', None)
    if db_session is not None:
        db_session.close()

# --- Маршруты (API) ---

@app.route("/")
def show_meme():
    session = get_db_session()
    
    reacted_meme_ids_query = session.query(Reaction.meme_id).distinct()
    reacted_ids = [id_tuple[0] for id_tuple in reacted_meme_ids_query.all()]
    
    unseen_memes_query = session.query(Meme).filter(not_(Meme.id.in_(reacted_ids)))
    unseen_memes = unseen_memes_query.all()
    
    next_meme = None
    
    if recommender.is_trained and unseen_memes:
        print(f"Модель обучена. Подбираю лучший мем из {len(unseen_memes)}...")
        unseen_memes_df = pd.DataFrame([{'id': m.id, 'source': m.source} for m in unseen_memes])
        
        scores = recommender.predict_scores(unseen_memes_df)
        unseen_memes_df['score'] = scores
        
        best_meme_row = unseen_memes_df.sort_values(by='score', ascending=False).iloc[0]
        best_meme_id = int(best_meme_row['id'])
        next_meme = session.query(Meme).get(best_meme_id)
        print(f"Выбран мем ID {next_meme.id} с оценкой {best_meme_row['score']:.2f}")

    else:
        if unseen_memes:
             print("Модель не обучена. Выбираю случайный из непросмотренных мемов.")
             next_meme = random.choice(unseen_memes)
        else:
            print("Все мемы просмотрены! Выбираю случайный из всех.")
            all_memes = session.query(Meme).all()
            if not all_memes:
                return "В базе данных нет мемов! Сначала запустите парсер."
            next_meme = random.choice(all_memes)

    model_is_trained = recommender.is_trained

    return render_template('index.html', 
                           meme_id=next_meme.id,
                           meme_title=next_meme.title, 
                           meme_url=next_meme.url,
                           model_is_trained=model_is_trained)


@app.route("/analyze", methods=['POST'])
def analyze_emotion():
    session = get_db_session()
    try:
        data = request.get_json()
        image_data = data['image']
        meme_id = data.get('meme_id')
        if not meme_id:
            return jsonify({'emotion': 'ошибка: нет meme_id'}), 400

        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        nparr = np.frombuffer(binary_data, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        result = DeepFace.analyze(img_np, actions=['emotion'], enforce_detection=False, silent=True)
        
        dominant_emotion = "лицо не найдено"
        if isinstance(result, list) and len(result) > 0:
            dominant_emotion = result[0]['dominant_emotion']
        
        if dominant_emotion != "лицо не найдено":
            existing_reaction = session.query(Reaction).filter_by(meme_id=meme_id).first()

            if not existing_reaction:
                new_reaction = Reaction(meme_id=meme_id, dominant_emotion=dominant_emotion)
                session.add(new_reaction)
                session.commit()
                print(f"Сохранена ПЕРВАЯ реакция '{dominant_emotion}' для мема ID {meme_id}")
            else:
                current_priority = EMOTION_PRIORITY.get(existing_reaction.dominant_emotion, 0)
                new_priority = EMOTION_PRIORITY.get(dominant_emotion, 0)

                if new_priority > current_priority:
                    existing_reaction.dominant_emotion = dominant_emotion
                    session.commit()
                    print(f"Обновлена реакция для мема ID {meme_id} на более важную: '{dominant_emotion}'")

        return jsonify({'emotion': dominant_emotion})

    except Exception as e:
        print(f"Критическая ошибка в /analyze: {e}")
        return jsonify({'emotion': 'ошибка анализа'}), 500


@app.route("/train")
def train_model_endpoint():
    session = get_db_session()
    print("Получен запрос на обучение модели...")
    
    query = session.query(Reaction.dominant_emotion, Meme.source).join(Meme)
    reactions_df = pd.read_sql(query.statement, session.bind)
    
    if reactions_df.empty or len(reactions_df) < 10:
        message = f"Обучение невозможно. Собрано {len(reactions_df)} реакций, а нужно минимум 10."
        print(message)
        return jsonify({"message": message})

    recommender.train(reactions_df)
    
    message = f"Модель обучена на {len(reactions_df)} реакциях!"
    return jsonify({"message": message})


if __name__ == '__main__':
    app.run(debug=True)