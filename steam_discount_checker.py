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

from threading import Thread
from flask import Flask

from bs4 import BeautifulSoup

TOKEN = "8061572609:AAEo_zTrZ1wy3x53JswwlQYpwogsmE7bkgg"  # заміни на новий токен!


# Функція для отримання знижок зі Steam
def get_discounted_games():
    url = "https://store.steampowered.com/api/featuredcategories?cc=ua&l"
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
    url = "https://store.steampowered.com/api/storesearch/?term=Valheim&cc=ua&l"
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

def get_free_games():
    url = "https://store.steampowered.com/api/featuredcategories?cc=ua&l"
    response = requests.get(url).json()
    discounted = response.get("specials", {}).get("items", [])

    free_games = []
    for game in discounted:
        discount = game.get("discount_percent", 0)
        if discount == 100:
            name = game.get("name", "Без назви")
            original_price = game.get("original_price", 0) / 100
            free_games.append(f"{name}: 🎉 <b>Безкоштовно</b> (було {original_price}€)")

    return free_games[:20]  # максимум 20

def get_90_discount_games_from_page(offset=0):
    url = f"https://store.steampowered.com/specials/?l=ukrainian&offset={offset}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    game_blocks = soup.select(".tab_item")
    result = []

    for block in game_blocks:
        title = block.select_one(".tab_item_name").get_text(strip=True)
        discount_block = block.select_one(".discount_pct")
        if not discount_block:
            continue
        discount_text = discount_block.get_text(strip=True).replace("-", "").replace("%", "")
        try:
            discount_percent = int(discount_text)
        except ValueError:
            continue

        if discount_percent >= 90:
            old_price = block.select_one(".discount_original_price").get_text(strip=True)
            final_price = block.select_one(".discount_final_price").get_text(strip=True)
            result.append(f"{title}: -{discount_percent}% → {final_price} (було {old_price})")

    return result

def get_all_90_discount_games():
    all_games = []
    for offset in range(0, 240, 60):  # offset: 0, 60, 120, 180, 240
        games = get_90_discount_games_from_page(offset)
        all_games.extend(games)
    return all_games[:20]  # максимум 20 найвигідніших


# Стартова команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Показати знижки", callback_data="show_discounts")],
        [InlineKeyboardButton("🔨 Valheim", callback_data="show_valheim")],
        [InlineKeyboardButton("🆓 Ігри 100%", callback_data="show_free_games")],
        [InlineKeyboardButton("💯 Знижка 90%", callback_data="get_all_90_discount_games")],
        [InlineKeyboardButton("💯 Знижка з 90%", callback_data="get_90_discount_games_from_page")],
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

    elif query.data == "show_free_games":
        free_games = get_free_games()
        if free_games:
            message = "🆓 <b>Ігри зі знижкою 100%:</b>\n" + "\n".join(free_games)
        else:
            message = "Зараз немає безкоштовних ігор 😢"
        await query.edit_message_text(message, parse_mode="HTML")

    elif query.data == "get_all_90_discount":
        games = get_all_90_discount_games()
        if games:
            message = "💯 <b>Ігри зі знижкою 90% і більше:</b>\n" + "\n".join(games)
        else:
            message = "Зараз немає ігор зі знижкою 90% 😢"
        await query.edit_message_text(message, parse_mode="HTML")

    elif query.data == "show_90_discounts":
        games = get_all_90_discount_games()
        if games:
            message = "💯 <b>Ігри зі знижкою 90% і більше:</b>\n" + "\n".join(games)
        else:
            message = "Зараз немає ігор зі знижкою 90% 😢"
        await query.edit_message_text(message, parse_mode="HTML")


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

app = Flask('')

@app.route('/')
def home():
    return "Steam Discount Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Запуск бота
if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex('^Start$'), start))
    app.add_handler(CallbackQueryHandler(button_handler))

    schedule_daily_job(app)

    print("✅ Бот запущено. Очікую команди /start...")
    app.run_polling()

#8061572609:AAHDDh11pyNLkhujAELqfEKb6DSu2YzZm1U
#'chat': {'id': 1182819676}