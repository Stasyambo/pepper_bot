import logging
import os

from telebot.async_telebot import AsyncTeleBot
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import database as db
import parser
import asyncio
bot = AsyncTeleBot(os.environ["BOT_TOKEN"])
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.add_user(user_id)
    await update.message.reply_text(
        "Привет! Я бот для отслеживания скидок с Pepper.ru.\n"
        "Отправь мне ключевые слова через запятую, и я буду присылать тебе уведомления о новых скидках, которые под них подходят.\n"
        "Например: nike, adidas, playstation 5"
    )


# Обработчик текстовых сообщений (ключевых слов)
async def handle_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_keywords = update.message.text

    # Сохраняем ключевые слова в БД
    db.update_user_keywords(user_id, user_keywords)
    await update.message.reply_text(f"Отлично! Буду искать для тебя скидки по словам: {user_keywords}")


# Функция проверки новых сделок и рассылки уведомлений
async def check_deals_and_notify(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Запуск проверки новых сделок...")
    deals = parser.parse_pepper()
    subscriptions = db.get_all_subscriptions()

    # Получаем ID уже отправленных сделок
    sent_deal_ids = set(db.get_all_sent_deal_ids())

    logger.info(f"Найдено {len(deals)} сделок, {len(subscriptions)} подписок")

    new_deals_found = 0
    notifications_sent = 0

    for deal in deals:
        deal_id = deal['id']

        # Пропускаем уже отправленные сделки
        if deal_id in sent_deal_ids:
            continue

        deal_title = deal['title'].lower()

        for user_id, keywords in subscriptions.items():
            keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
            for keyword in keyword_list:
                if keyword and keyword in deal_title:
                    message = (
                        f"🔥 Новая скидка!\n\n"
                        f"{deal['title']}\n\n"
                        f"🏪 Магазин: {deal['store']}\n"
                        f"💰 Цена: {deal['price']}\n"
                        f"❤️  Температура: {deal['temperature']}\n\n"
                        f"🔗 Ссылка: {deal['link']}"
                    )
                    try:
                        await context.bot.send_message(chat_id=user_id, text=message)
                        logger.info(f"Уведомление отправлено пользователю {user_id} по слову '{keyword}'")

                        # Помечаем сделку как отправленную
                        db.add_sent_deal(deal_id, deal)
                        new_deals_found += 1
                        notifications_sent += 1

                        await asyncio.sleep(1)
                        break
                    except Exception as e:
                        logger.error(f"Ошибка отправки: {e}")

    logger.info(f"Найдено {new_deals_found} новых сделок, отправлено {notifications_sent} уведомлений")
    return new_deals_found, notifications_sent


# Тестовая команда
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для немедленной проверки"""
    user_id = update.effective_user.id
    await update.message.reply_text("Запускаю тестовую проверку...")

    # Немедленно проверяем сделки
    new_deals, notifications = await check_deals_and_notify(context)
    await update.message.reply_text(
        f"Тестовая проверка завершена!\n"
        f"Найдено новых сделок: {new_deals}\n"
        f"Отправлено уведомлений: {notifications}"
    )


async def scheduled_task(app):
    """Фоновая задача для периодической проверки"""
    while True:
        try:
            logger.info("Запуск плановой проверки...")
            await check_deals_and_notify(app)
            logger.info("Плановая проверка завершена")
        except Exception as e:
            logger.error(f"Ошибка в плановой проверке: {e}")
        # Ждем 3 минуты между проверками
        await asyncio.sleep(180)


def main():
    # Инициализируем базу данных
    db.init_db()

    # Очищаем старые сделки при старте
    db.cleanup_old_deals(7)

    # Создаем Application и передаем ему токен бота
    application = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keywords))

    # Запускаем фоновую задачу при старте
    application.job_queue.run_once(lambda ctx: asyncio.create_task(scheduled_task(ctx.application)), when=5)

    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()
