import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

import sys
import subprocess
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import time

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time as dtime
import asyncio

TOKEN = "8061572609:AAHDDh11pyNLkhujAELqfEKb6DSu2YzZm1U"  # заміни на новий токен!


# Функція для отримання знижок зі Steam
def get_discounted_games():
    url = "https://store.steampowered.com/api/featuredcategories?cc=ua&l=ukrainian"
    response = requests.get(url).json()
    discounted = response.get("specials", {}).get("items", [])

    games_on_sale = []
    for game in discounted:
        name = game.get("name")
        discount = game.get("discount_percent")
        if discount > 0:
            price = game.get("final_price") / 100
            old_price = game.get("original_price") / 100
            games_on_sale.append(f"{name}: -{discount}% → {price}€ (було {old_price}€)")
    return games_on_sale[:20]  # максимум 5


# Функція для отримання знижки на конкретну гру (Valheim)
def get_valheim_discount():
    url = "https://store.steampowered.com/api/storesearch/?term=Valheim&cc=ua&l=ukrainian"
    response = requests.get(url).json()
    games = response.get("items", [])

    steam_link = "https://store.steampowered.com/app/892970/Valheim/"

    for game in games:
        if "Valheim" in game.get("name", ""):
            discount = game.get("discount_percent", 0)
            final_price = game.get("final_price")
            original_price = game.get("original_price")

            # Клікабельна назва з посиланням
            game_name_linked = f'<a href="{steam_link}">Valheim</a>'

            if final_price is not None:
                price = final_price / 100
                if discount > 0 and original_price is not None:
                    old_price = original_price / 100
                    return f"{game_name_linked}: -{discount}% → {price}€ (було {old_price}€)"
                else:
                    return f"{game_name_linked}: {price}€ (без знижки)"
            else:
                return f"{game_name_linked}: ціна недоступна 😢"

    return "Гру Valheim не знайдено 😢"


# Стартова команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Показати знижки", callback_data="show_discounts")],
        [InlineKeyboardButton("🔨 Valheim", callback_data="show_valheim")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привіт! Натисни кнопку нижче, щоб побачити знижки на Steam:",
                                    reply_markup=reply_markup)


# Обробка натискання кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_discounts":
        games = get_discounted_games()
        if games:
            message = "🎮 <b>Знижки в Steam:</b>\n" + "\n".join(games)
        else:
            message = "Зараз немає знижок 😢"
        await query.edit_message_text(message, parse_mode="HTML")

    elif query.data == "show_valheim":
        valheim_discount = get_valheim_discount()
        await query.edit_message_text(valheim_discount, parse_mode="HTML")

async def send_daily_discounts(application):
    games = get_discounted_games()
    if games:
        message = "🎮 <b>Щоденні знижки в Steam:</b>\n" + "\n".join(games)
    else:
        message = "Сьогодні немає знижок 😢"

    await application.bot.send_message(
        chat_id="1182819676",  # ← твій Chat ID
        text=message,
        parse_mode="HTML"
    )

def schedule_daily_job(application):
    scheduler = BackgroundScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_discounts(application)),
        trigger='cron',
        hour=19,
        minute=20
    )
    scheduler.start()

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex('^Start$'), start))
    app.add_handler(CallbackQueryHandler(button_handler))

    schedule_daily_job(app)

    print("✅ Бот запущено. Очікую команди /start...")
    app.run_polling()

#8061572609:AAHDDh11pyNLkhujAELqfEKb6DSu2YzZm1U
#'chat': {'id': 1182819676}