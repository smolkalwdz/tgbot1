# Система учета кальянов с Telegram ботом

Система для учета покупок кальянов с автоматическим предоставлением каждого 6-го кальяна бесплатно. Включает в себя Telegram бота для клиентов и веб-панель администратора для генерации QR-кодов.

## Функциональность

- Telegram бот для клиентов
- Веб-панель администратора
- Генерация QR-кодов для покупок
- Автоматический учет бесплатных кальянов (каждый 6-й)
- База данных для хранения информации о пользователях и покупках

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd hookah-bot
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` и добавьте в него токен бота:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Запуск

1. Запустите Telegram бота:
```bash
python bot.py
```

2. В отдельном терминале запустите веб-приложение:
```bash
uvicorn web_app:app --reload
```

Веб-панель администратора будет доступна по адресу: http://localhost:8000

## Использование

### Telegram бот

- `/start` - начать использование бота
- `/status` - проверить текущее количество покупок и прогресс до бесплатного кальяна

### Веб-панель администратора

1. Откройте http://localhost:8000
2. Найдите нужного пользователя в списке
3. Нажмите "Сгенерировать QR" для создания QR-кода новой покупки
4. QR-код будет показан на странице

## Структура проекта

- `bot.py` - Telegram бот
- `web_app.py` - FastAPI веб-приложение
- `database.py` - модели базы данных
- `templates/` - HTML шаблоны
- `static/` - статические файлы и QR-коды

# Telegram Bot Deployment Guide

## Локальный запуск
1. Установите Python 3.11 или выше
2. Установите зависимости: `pip install -r requirements.txt`
3. Создайте файл `.env` и добавьте в него токен бота:
   ```
   BOT_TOKEN=your_bot_token_here
   ```
4. Запустите бота: `python bot.py`

## Развертывание на PythonAnywhere (Рекомендуется)

1. Создайте аккаунт на [PythonAnywhere](https://www.pythonanywhere.com/)
2. Перейдите в раздел "Files" и загрузите все файлы проекта
3. В разделе "Consoles" откройте Bash консоль
4. Выполните команды:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Создайте файл `.env` с токеном бота
6. В разделе "Tasks" добавьте задачу:
   - Command: `python /home/yourusername/bot.py`
   - Schedule: Always
7. Нажмите кнопку "Create"

## Развертывание на Heroku

1. Установите [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Войдите в аккаунт: `heroku login`
3. Создайте приложение: `heroku create your-app-name`
4. Добавьте токен бота в настройки:
   ```bash
   heroku config:set BOT_TOKEN=your_bot_token_here
   ```
5. Разверните приложение:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```
6. Запустите worker: `heroku ps:scale worker=1`

## Развертывание на DigitalOcean

1. Создайте Droplet (Ubuntu)
2. Подключитесь по SSH
3. Установите необходимые пакеты:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv
   ```
4. Клонируйте репозиторий
5. Создайте и активируйте виртуальное окружение:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
6. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
7. Создайте systemd service:
   ```bash
   sudo nano /etc/systemd/system/telegram-bot.service
   ```
   ```ini
   [Unit]
   Description=Telegram Bot
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/root/your-bot-directory
   Environment="BOT_TOKEN=your_bot_token_here"
   ExecStart=/root/your-bot-directory/venv/bin/python bot.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
8. Запустите сервис:
   ```bash
   sudo systemctl enable telegram-bot
   sudo systemctl start telegram-bot
   ```

## Мониторинг
- PythonAnywhere: Раздел "Tasks" и логи
- Heroku: `heroku logs --tail`
- DigitalOcean: `journalctl -u telegram-bot.service -f` 