import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from sqlalchemy.orm import Session
from database import SessionLocal, User, Purchase
import qrcode
from datetime import datetime
import random
import string
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import asyncio

load_dotenv()

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Изменено с INFO на DEBUG для более подробного логирования
)

logger = logging.getLogger(__name__)

# Bot token
TOKEN = "7822698775:AAFqP42YD5nsKIrkrQ54h4ZD-kSJX2VXhHA"

# Список администраторов
ADMIN_IDS = [885843500]  # Ваш ID уже добавлен

def get_user_keyboard(is_admin: bool):
    """Создает клавиатуру в зависимости от прав пользователя"""
    keyboard = [
        [KeyboardButton("📊 Моя статистика"), KeyboardButton("👤 Мой профиль")],
    ]
    if is_admin:
        keyboard.extend([
            [KeyboardButton("🎯 Сканировать QR"), KeyboardButton("✨ Создать QR")],
            [KeyboardButton("📢 Отправить рассылку")]
        ])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений и кнопок"""
    text = update.message.text
    
    if text == "📊 Моя статистика":
        await status(update, context)
    elif text == "👤 Мой профиль":
        await profile(update, context)
    elif text == "🎯 Сканировать QR":
        await scan(update, context)
    elif text == "✨ Создать QR":
        if not context.args:
            context.args = []  # Инициализируем пустой список аргументов
        await generate(update, context)
    elif text == "📢 Отправить рассылку":
        if not context.args:
            context.args = []  # Инициализируем пустой список аргументов
        await broadcast(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = update.effective_user
    
    # Check if user exists in database
    db_user = db.query(User).filter(User.telegram_id == user.id).first()
    if not db_user:
        db_user = User(
            telegram_id=user.id,
            username=user.username,
            purchases_count=0
        )
        db.add(db_user)
        db.commit()
    
    is_admin = user.id in ADMIN_IDS
    
    # Создаем клавиатуру
    reply_markup = get_user_keyboard(is_admin)
    
    welcome_message = (
        f"Привет, {user.first_name}! 👋\n\n"
        f"Ваш Telegram ID: {user.id}\n"
        "Добро пожаловать в систему учета кальянов тайм кафе Dungeon!\n"
        "Каждый 6-й кальян бесплатный! 🎉\n\n"
        f"У вас сейчас {db_user.purchases_count} купленных кальянов.\n\n"
        "Используйте кнопки меню для навигации:"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    # Проверяем наличие активного QR-кода
    active_qr = db.query(Purchase).filter(
        Purchase.user_id == db_user.id,
        Purchase.verified == False
    ).first()
    
    if not active_qr:
        # Создаем новый QR-код
        qr_code_data = generate_qr_code()
        is_free = (db_user.purchases_count + 1) % 6 == 0
        
        # Создаем запись о покупке
        purchase = Purchase(
            user_id=db_user.id,
            qr_code=qr_code_data,
            is_free=is_free
        )
        db.add(purchase)
        db.commit()
        
        # Создаем QR-код
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_code_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем изображение в буфер
        bio = BytesIO()
        qr_image.save(bio, 'PNG')
        bio.seek(0)
        
        await update.message.reply_photo(
            photo=bio,
            caption=f"Ваш {'🎁 бесплатный' if is_free else '💰 обычный'} QR-код готов!\n"
                    "Покажите его администратору при оплате."
        )
    
    db.close()

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет прав для использования этой команды.")
        return
    
    # Проверяем, указан ли ID пользователя
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите ID пользователя.\n"
            "Пример: /generate 123456789"
        )
        return
    
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID пользователя должен быть числом.")
        return
    
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()
    
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        db.close()
        return
    
    # Проверяем активные QR-коды
    active_qr = db.query(Purchase).filter(
        Purchase.user_id == user.id,
        Purchase.verified == False
    ).first()
    
    if active_qr:
        # Создаем QR-код из существующего кода
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(active_qr.qr_code)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем изображение в буфер
        bio = BytesIO()
        qr_image.save(bio, 'PNG')
        bio.seek(0)
        
        await update.message.reply_photo(
            photo=bio,
            caption=f"Существующий {'бесплатный' if active_qr.is_free else 'обычный'} QR-код для пользователя."
        )
        db.close()
        return
    
    # Генерируем новый QR-код
    qr_code_data = generate_qr_code()
    
    # Создаем QR-код
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_code_data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем изображение в буфер
    bio = BytesIO()
    qr_image.save(bio, 'PNG')
    bio.seek(0)
    
    # Создаем запись о покупке
    is_free = (user.purchases_count + 1) % 6 == 0
    purchase = Purchase(
        user_id=user.id,
        qr_code=qr_code_data,
        is_free=is_free
    )
    db.add(purchase)
    
    # Обновляем счетчики пользователя
    user.purchases_count += 1
    if is_free:
        user.total_free_hookahs += 1
    
    db.commit()
    
    # Отправляем QR-код в чат
    await update.message.reply_photo(
        photo=bio,
        caption=f"{'🎁 Бесплатный' if is_free else '💰 Обычный'} QR-код для пользователя."
    )
    
    # Пытаемся уведомить пользователя
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Для вас создан новый {'бесплатный' if is_free else 'обычный'} QR-код!\n"
                 f"Посмотреть его можно в личном кабинете: http://localhost:8000/guest/{user_id}"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю: {e}")
    
    db.close()

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Пожалуйста, начните с команды /start")
        db.close()
        return
    
    purchases_until_free = 6 - (user.purchases_count % 6)
    
    # Получаем активный QR-код
    active_qr = db.query(Purchase).filter(
        Purchase.user_id == user.id,
        Purchase.verified == False
    ).first()
    
    qr_status = "\n\n✨ У вас есть активный QR-код! Используйте /profile чтобы посмотреть его." if active_qr else ""
    
    await update.message.reply_text(
        f"📊 Ваша статистика:\n\n"
        f"🔸 Купленных кальянов: {user.purchases_count}\n"
        f"🎁 Полученных бесплатных кальянов: {user.total_free_hookahs}\n"
        f"🎯 До следующего бесплатного кальяна: {purchases_until_free}"
        f"{qr_status}"
    )
    db.close()

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile_url = f"http://localhost:8000/guest/{user_id}"
    
    db = SessionLocal()
    # Получаем активный QR-код
    active_qr = db.query(Purchase).filter(
        Purchase.user_id == db.query(User).filter(User.telegram_id == user_id).first().id,
        Purchase.verified == False
    ).first()
    
    if active_qr:
        # Создаем QR-код
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(active_qr.qr_code)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем изображение в буфер
        bio = BytesIO()
        qr_image.save(bio, 'PNG')
        bio.seek(0)
        
        await update.message.reply_photo(
            photo=bio,
            caption=f"Ваш текущий {'бесплатный' if active_qr.is_free else 'обычный'} QR-код.\n\n"
                    f"🌐 Веб-версия личного кабинета:\n{profile_url}"
        )
    else:
        await update.message.reply_text(
            "У вас нет активных QR-кодов.\n\n"
            f"🌐 Веб-версия личного кабинета:\n{profile_url}"
        )
    
    db.close()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет прав для сканирования QR-кодов.")
        return
    
    # Получаем фото в максимальном размере
    photo = await update.message.photo[-1].get_file()
    
    # Скачиваем фото во временный файл
    photo_path = f"temp_{update.effective_user.id}.jpg"
    await photo.download_to_drive(photo_path)
    
    try:
        # Читаем изображение с помощью OpenCV
        image = cv2.imread(photo_path)
        
        # Конвертируем в grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Пытаемся найти QR-код
        decoded_objects = decode(gray)
        
        if not decoded_objects:
            await update.message.reply_text("❌ QR-код не найден на изображении. Попробуйте сделать фото более четким.")
            return
        
        # Получаем данные из QR-кода
        qr_data = decoded_objects[0].data.decode('utf-8')
        
        # Проверяем QR-код в базе данных
        db = SessionLocal()
        purchase = db.query(Purchase).filter(
            Purchase.qr_code == qr_data,
            Purchase.verified == False
        ).first()
        
        if not purchase:
            await update.message.reply_text("❌ Недействительный QR-код. Возможно, он уже был использован или не существует.")
            db.close()
            return
        
        # Получаем информацию о пользователе
        user = db.query(User).filter(User.id == purchase.user_id).first()
        
        if not user:
            await update.message.reply_text("❌ Ошибка: пользователь не найден в базе данных.")
            db.close()
            return
        
        # Помечаем QR-код как использованный
        purchase.verified = True
        
        # Обновляем счетчик купленных кальянов
        if not purchase.is_free:
            user.purchases_count += 1
        else:
            user.total_free_hookahs += 1
        
        # Проверяем, нужно ли создать новый бесплатный QR-код
        next_purchase_free = (user.purchases_count % 6 == 0)
        
        db.commit()
        
        # Формируем сообщение об успешном сканировании
        message_text = (
            f"✅ QR-код успешно отсканирован!\n\n"
            f"👤 Пользователь: {user.username or 'Неизвестно'}\n"
            f"🎯 Тип: {'🎁 Бесплатный' if purchase.is_free else '💰 Обычный'} кальян\n"
            f"📊 Всего кальянов: {user.purchases_count}\n"
            f"🎁 Бесплатных использовано: {user.total_free_hookahs}\n"
            f"🎯 До следующего бесплатного: {6 - (user.purchases_count % 6)}"
        )
        
        await update.message.reply_text(message_text)
        
        # Уведомляем пользователя
        user_message = (
            f"✅ Ваш {'бесплатный' if purchase.is_free else 'обычный'} QR-код был успешно использован!\n\n"
            f"📊 У вас теперь {user.purchases_count} купленных кальянов\n"
            f"🎁 Использовано бесплатных: {user.total_free_hookahs}\n"
            f"🎯 До следующего бесплатного: {6 - (user.purchases_count % 6)}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=user_message
            )
            
            # Если следующий кальян будет бесплатным, создаем новый QR-код
            if next_purchase_free:
                # Создаем новый QR-код
                qr_code_data = generate_qr_code()
                new_purchase = Purchase(
                    user_id=user.id,
                    qr_code=qr_code_data,
                    is_free=True
                )
                db.add(new_purchase)
                db.commit()
                
                # Создаем QR-код
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_code_data)
                qr.make(fit=True)
                qr_image = qr.make_image(fill_color="black", back_color="white")
                
                # Сохраняем изображение в буфер
                bio = BytesIO()
                qr_image.save(bio, 'PNG')
                bio.seek(0)
                
                # Отправляем новый QR-код пользователю
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text="🎉 Поздравляем! Вы получили бесплатный кальян!"
                )
                await context.bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=bio,
                    caption="🎁 Ваш QR-код на бесплатный кальян"
                )
        
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю: {e}")
        
        db.close()
        
    except Exception as e:
        logging.error(f"Ошибка при сканировании QR-кода: {e}")
        await update.message.reply_text("❌ Произошла ошибка при сканировании QR-кода. Попробуйте еще раз.")
    
    finally:
        # Удаляем временный файл
        if os.path.exists(photo_path):
            os.remove(photo_path)

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет прав для использования этой команды.")
        return
    
    await update.message.reply_text(
        "📸 Для сканирования QR-кода:\n\n"
        "1. Сделайте фото QR-кода\n"
        "2. Отправьте фото в этот чат\n"
        "3. Я проверю QR-код и подтвержу покупку"
    )

async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"Ваш Telegram ID: {user.id}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка рассылки всем пользователям"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет прав для отправки рассылки.")
        return
    
    # Проверяем, есть ли текст сообщения
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Как использовать команду:\n\n"
            "/broadcast Текст сообщения\n\n"
            "Примеры:\n"
            "/broadcast 🎉 Акция! Сегодня все кальяны -20%\n"
            "/broadcast �� Новые вкусы в меню Dungeon!\n"
            "/broadcast ⚡️ Только сегодня в Dungeon: при заказе кальяна - чай в подарок"
        )
        return
    
    # Получаем текст рассылки
    broadcast_text = " ".join(context.args)
    
    # Получаем всех пользователей из базы
    db = SessionLocal()
    users = db.query(User).all()
    
    success_count = 0
    fail_count = 0
    
    await update.message.reply_text("📤 Начинаю рассылку...")
    
    # Отправляем сообщение каждому пользователю
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 Новость от тайм кафе Dungeon:\n\n{broadcast_text}",
                parse_mode='HTML'
            )
            success_count += 1
            # Небольшая задержка между отправками
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {user.telegram_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"✓ Успешно отправлено: {success_count}\n"
        f"❌ Ошибок отправки: {fail_count}"
    )
    
    db.close()

async def check_free_hookah(context: ContextTypes.DEFAULT_TYPE):
    """Проверка и уведомление о бесплатных кальянах"""
    db = SessionLocal()
    users = db.query(User).all()
    
    for user in users:
        remaining = 6 - (user.purchases_count % 6)
        
        # Проверяем наличие неиспользованного бесплатного QR-кода
        free_qr = db.query(Purchase).filter(
            Purchase.user_id == user.id,
            Purchase.is_free == True,
            Purchase.verified == False
        ).first()
        
        if free_qr:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text="🎁 Напоминаем, что у вас есть неиспользованный бесплатный кальян в тайм кафе Dungeon!\n"
                         "Используйте команду /profile чтобы посмотреть ваш QR-код."
                )
            except Exception as e:
                logging.error(f"Не удалось отправить напоминание пользователю {user.telegram_id}: {e}")
        elif remaining <= 3:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"🎯 До получения бесплатного кальяна в тайм кафе Dungeon осталось всего {remaining} {'кальян' if remaining == 1 else 'кальяна' if remaining < 5 else 'кальянов'}!\n"
                         f"Приходите к нам снова 😊"
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление пользователю {user.telegram_id}: {e}")
    
    db.close()

def generate_qr_code():
    # Generate random string for QR code
    letters_and_digits = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(letters_and_digits) for i in range(20))
    return random_string

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Exception while handling an update: {context.error}")
    await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")

def main():
    logger.info("Starting bot initialization...")
    
    if not TOKEN:
        logger.error("No token provided!")
        return

    try:
        logger.info("Building application...")
        application = Application.builder().token(TOKEN).build()

        # Add handlers
        logger.info("Adding handlers...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(CommandHandler("profile", profile))
        application.add_handler(CommandHandler("scan", scan))
        application.add_handler(CommandHandler("generate", generate))
        application.add_handler(CommandHandler("myid", get_my_id))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Добавляем периодическую проверку бесплатных кальянов
        logger.info("Setting up job queue...")
        job_queue = application.job_queue
        job_queue.run_repeating(check_free_hookah, interval=86400)
        
        # Add error handler
        application.add_error_handler(error_handler)

        logger.info("Starting polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error during bot initialization: {e}", exc_info=True)

if __name__ == '__main__':
    logger.info("Bot script started")
    main() 