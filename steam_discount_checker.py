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
    url = "https://store.steampowered.com/api/storesearch/?term=Valheim&cc=ua&l=uk"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "uk-UA,uk;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        games = response.json().get("items", [])

        steam_link = "https://store.steampowered.com/app/892970/Valheim/"

        for game in games:
            if "Valheim" in game.get("name", ""):
                discount = game.get("discount_percent", 0)
                final_price = game.get("final_price")
                original_price = game.get("original_price")
                currency = game.get("price_currency", "₴")  # за замовчуванням гривня

                # Клікабельна назва з посиланням
                game_name_linked = f'<a href="{steam_link}">Valheim</a>'

                if final_price is not None:
                    price = final_price / 100
                    if discount > 0 and original_price:
                        old_price = original_price / 100
                        return f"{game_name_linked}: -{discount}% → {price}{currency} (було {old_price}{currency})"
                    else:
                        return f"{game_name_linked}: {price}{currency} (без знижки)"
                else:
                    return f"{game_name_linked}: ціна недоступна 😢"

        return "Гру Valheim не знайдено 😢"

    except Exception as e:
        print(f"Помилка при отриманні знижки для Valheim: {e}")
        return "Сталася помилка при запиті 😢"


def get_free_games():
    url = "https://store.steampowered.com/search/results/?query&start=0&count=20&dynamic_data=&sort_by=_ASC&snr=1_7_7_7000_7&maxprice=free&specials=1&infinite=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "uk-UA,uk;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        soup = BeautifulSoup(data['results_html'], 'html.parser')

        free_games = []

        for game in soup.select('a.search_result_row'):
            title = game.select_one('.title').text.strip()
            discount_block = game.select_one('.search_discount_block')
            if discount_block:
                discount_pct = discount_block.select_one('.discount_pct')
                if discount_pct and "-100%" in discount_pct.text:
                    original_price = discount_block.select_one('.discount_original_price')
                    original_price_text = original_price.text.strip() if original_price else "?"
                    free_games.append(f"{title}: 🎉 <b>Безкоштовно</b> (було {original_price_text})")

        return free_games if free_games else None

    except Exception as e:
        print(f"Помилка при отриманні безкоштовних ігор: {e}")
        return None

def get_90_discount_games():
    url = "https://store.steampowered.com/search/results/?query&start=0&count=50&dynamic_data=&sort_by=Discount_DESC&snr=1_7_7_230_7&specials=1&infinite=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "uk-UA,uk;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        soup = BeautifulSoup(data['results_html'], 'html.parser')

        discount_games = []

        for game in soup.select('a.search_result_row'):
            title = game.select_one('.title').text.strip()
            discount_block = game.select_one('.search_discount_block')
            if not discount_block:
                continue

            discount_pct = discount_block.select_one('.discount_pct')
            if not discount_pct:
                continue

            discount_value = int(discount_pct.text.strip().replace('-', '').replace('%', ''))
            if discount_value >= 90:
                original_price = discount_block.select_one('.discount_original_price')
                final_price = discount_block.select_one('.discount_final_price')
                link = game['href'].split('?')[0]

                discount_games.append(
                    f'<a href="{link}">{title}</a>: -{discount_value}% → {final_price.text.strip()} (було {original_price.text.strip()})'
                )

        return discount_games[:20] if discount_games else None

    except Exception as e:
        print(f"Помилка при отриманні ігор зі знижкою 90%: {e}")
        return None

def show_rozdacha():
    url = "https://store.steampowered.com/sale/special_deals"
    return f'🛍️ <b>Steam розпродаж:</b>\n<a href="{url}">Переглянути знижки тут</a>'

# Стартова команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Показати знижки", callback_data="show_discounts")],
        [InlineKeyboardButton("🔨 Valheim", callback_data="show_valheim")],
        [InlineKeyboardButton("🆓 Ігри 100%", callback_data="show_free_games")],
        [InlineKeyboardButton("💯 Знижка 90%+", callback_data="show_90_discounts")],
        [InlineKeyboardButton("👌 Розпродажі", callback_data="show_rozdacha")],
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

    elif query.data == "show_90_discounts":
        games = get_90_discount_games()
        if games:
            message = "💯 <b>Ігри зі знижкою 90% і більше:</b>\n" + "\n".join(games)
        else:
            url = "https://store.steampowered.com/sale/special_deals"
            message = f"Зараз немає ігор зі знижкою 90% 😢 {url}"
        await query.edit_message_text(message, parse_mode="HTML")

    elif query.data == "show_rozdacha":
        message = show_rozdacha()
        await query.edit_message_text(message, parse_mode="HTML", disable_web_page_preview=False)


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