// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    
    // --- Получаем все нужные элементы со страницы ---
    const videoElement = document.getElementById('webcam');
    const emotionResultElement = document.getElementById('emotion-result');
    const trainButton = document.getElementById('trainButton');
    let analysisInterval;

    // --- Функция для отправки кадра на анализ ---
    async function analyzeFrame() {
        // Проверяем, готова ли камера к работе
        if (!videoElement.srcObject || videoElement.paused || videoElement.ended) {
            return; // Не анализируем, если видео неактивно
        }

        // Читаем ID текущего мема из скрытого поля
        const memeId = document.getElementById('memeId').value;
        if (!memeId) {
            console.error("Не найден ID мема на странице!");
            return;
        }

        // 1. Создаем "холст" (canvas), чтобы сделать снимок с видео
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        const context = canvas.getContext('2d');
        
        // 2. "Рисуем" текущий кадр с видео на холсте
        // Зеркалим изображение по горизонтали, чтобы оно соответствовало виду в камере
        context.translate(canvas.width, 0);
        context.scale(-1, 1);
        context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

        // 3. Получаем изображение с холста в формате Base64
        const imageData = canvas.toDataURL('image/jpeg');

        try {
            // 4. Отправляем изображение и ID мема на наш бэкенд-API
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData, meme_id: memeId }),
            });

            if (!response.ok) {
                throw new Error(`Ошибка сервера: ${response.status}`);
            }

            // 5. Получаем результат анализа и отображаем его
            const result = await response.json();
            emotionResultElement.textContent = translateEmotion(result.emotion);

        } catch (error) {
            console.error('Ошибка при отправке кадра на анализ:', error);
            // Если анализ не удался, останавливаем его, чтобы не спамить ошибками
            if (analysisInterval) clearInterval(analysisInterval);
        }
    }

    // Простая функция для перевода эмоций на русский язык и добавления иконок
    function translateEmotion(emotion) {
        const translations = {
            'angry': 'Злость 😠',
            'disgust': 'Отвращение 🤢',
            'fear': 'Страх 😨',
            'happy': 'Радость 😄',
            'sad': 'Грусть 😢',
            'surprise': 'Удивление 😮',
            'neutral': 'Нейтрально 😐',
            'face not found': 'Лицо не найдено',
            'ошибка анализа': 'Ошибка анализа'
        };
        return translations[emotion] || emotion;
    }


    // --- Логика для кнопки обучения ---
    trainButton.addEventListener('click', async () => {
        trainButton.disabled = true;
        trainButton.textContent = 'Обучение...';

        try {
            const response = await fetch('/train'); // Отправляем запрос на обучение
            const result = await response.json();

            // Показываем результат прямо на кнопке
            trainButton.textContent = result.message;

        } catch (error) {
            console.error('Ошибка при запуске обучения:', error);
            trainButton.textContent = 'Ошибка! См. консоль';
        } finally {
            // Через 3 секунды возвращаем кнопку в исходное состояние,
            // чтобы пользователь мог запустить обучение снова позже.
            setTimeout(() => {
                trainButton.disabled = false;
                trainButton.textContent = 'Обучить модель';
            }, 3000); // 3000 миллисекунд = 3 секунды
        }
    });


    // --- Инициализация камеры при загрузке страницы ---
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                videoElement.srcObject = stream;
                videoElement.play();
                console.log("Веб-камера успешно подключена!");

                // После успешного подключения камеры, запускаем анализ
                // с заданной периодичностью
                analysisInterval = setInterval(analyzeFrame, 1500); // 1.5 секунды
            })
            .catch(err => {
                console.error("Ошибка доступа к веб-камере: ", err);
                emotionResultElement.textContent = "Нет доступа к камере!";
            });
    } else {
        console.error("Ваш браузер не поддерживает доступ к веб-камере.");
        emotionResultElement.textContent = "Камера не поддерживается";
    }
});