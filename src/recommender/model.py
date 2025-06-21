# src/recommender/model.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib # Библиотека для сохранения и загрузки моделей

class MemeRecommender:
    def __init__(self):
        # Мы будем использовать простую логистическую регрессию.
        # Она отлично подходит для бинарной классификации (нравится/не нравится).
        # OneHotEncoder превращает текстовые категории (источник мема) в числа.
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore'), ['source'])
            ])
        
        self.pipeline = Pipeline(steps=[('preprocessor', preprocessor),
                                        ('classifier', LogisticRegression(class_weight='balanced'))])
        self.is_trained = False

    def train(self, reactions_df):
        """
        Обучает модель на данных из DataFrame.
        DataFrame должен содержать колонки 'dominant_emotion' и 'source'.
        """
        # 1. Готовим данные
        # Определяем целевую переменную y (что мы хотим предсказать)
        # 1 - "понравилось", 0 - "не понравилось"
        positive_emotions = ['happy', 'surprise']
        reactions_df['target'] = reactions_df['dominant_emotion'].apply(lambda x: 1 if x in positive_emotions else 0)

        # Определяем признаки X (на основе чего мы предсказываем)
        # Пока что у нас только один признак - источник мема.
        features = ['source']
        X = reactions_df[features]
        y = reactions_df['target']

        # Если у нас слишком мало данных или только один тип реакции, модель не обучить
        if len(reactions_df) < 10 or len(y.unique()) < 2:
            print("Недостаточно данных для обучения. Нужно хотя бы 10 реакций и 2 разных исхода.")
            return

        # 2. Обучаем модель (весь конвейер)
        print("Начинаю обучение модели...")
        self.pipeline.fit(X, y)
        self.is_trained = True
        print("Модель успешно обучена!")

        # 3. Сохраняем обученную модель в файл
        joblib.dump(self.pipeline, 'recommender_model.pkl')
        print("Модель сохранена в файл recommender_model.pkl")

    def predict_scores(self, memes_df):
        """
        Предсказывает вероятность "лайка" для новых мемов.
        """
        if not self.is_trained:
            # Если модель не обучена, возвращаем для всех мемов одинаковую вероятность
            return [0.5] * len(memes_df)
            
        # Используем модель для предсказания вероятностей
        # Нам нужна вероятность класса "1" (понравится)
        scores = self.pipeline.predict_proba(memes_df[['source']])[:, 1]
        return scores

    def load(self):
        """Загружает модель из файла."""
        try:
            self.pipeline = joblib.load('recommender_model.pkl')
            self.is_trained = True
            print("Модель успешно загружена из файла.")
        except FileNotFoundError:
            print("Файл модели не найден. Модель не загружена.")
            self.is_trained = False