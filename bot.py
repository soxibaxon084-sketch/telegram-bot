import json
import os
from datetime import datetime, timezone

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
import requests
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp

BOT_TOKEN = "8981578001:AAFRQHImB6Ry5bl6Q2OvcSTTlfytu7vUhKs"
DATA_FILE = "data.json"

FAQ = {
    "hours": "We're open 9am-6pm, Monday to Saturday.",
    "location": "We're located at 123 Example Street.",
    "price": "Prices start at $10. Message us for a full list!",
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user_data(data, user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"reminders": [], "expenses": []}
    return data[uid]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm DailyS Assistant.\n\n"
        "Commands:\n"
        "/faq <topic> - hours, location, price\n"
        "/remind <text> - save a reminder\n"
        "/reminders - list your reminders\n"
        "/expense <amount> <note> - log an expense\n"
        "/expenses - see your expense total\n"
        "/help - show this message"
    )
async def mylocation(update, context):
    button = KeyboardButton(text="Share my location", request_location=True)
    markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Tap the button below to share your location:",
        reply_markup=markup
    )

async def handle_location(update, context):
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "DailyS-Assistant-Bot"}
        )
        async def download(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /download <instagram or tiktok link>")
        return
    url = context.args[0]
    await update.message.reply_text("Downloading... this may take a moment.")
    ydl_opts = {
        "outtmpl": "downloaded_video.%(ext)s",
        "format": "mp4/best",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        with open("downloaded_video.mp4", "rb") as video_file:
            await update.message.reply_video(video=video_file)
    except Exception as e:
        await update.message.reply_text(f"Couldn't download that. Error: {e}")
        data = response.json()
        address = data.get("display_name", "Couldn't determine address.")
    except Exception:
        address = "Sorry, couldn't look up your location right now."
    await update.message.reply_text(f"You're at:\n{address}")
async def help_cmd(update, context):
    await start(update, context)

async def faq(update, context):
    if not context.args:
        await update.message.reply_text("Ask about: hours, location, price\nUsage: /faq hours")
        return
    topic = context.args[0].lower()

    if topic == "hours":
        now_utc = datetime.now(timezone.utc).strftime("%H:%M UTC on %B %d, %Y")
        answer = f"The current time is {now_utc}."
    elif topic == "location":
        answer = "Use /mylocation to share your live location and get your address!"
    else:
        answer = FAQ.get(topic, "Sorry, I don't have an answer for that yet.")

    await update.message.reply_text(answer)

async def remind(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /remind Buy groceries")
        return
    text = " ".join(context.args)
    data = load_data()
    user = get_user_data(data, update.effective_user.id)
    user["reminders"].append({"text": text, "created": datetime.now().strftime("%Y-%m-%d %H:%M")})
    save_data(data)
    await update.message.reply_text(f"Reminder saved: {text}")

async def list_reminders(update, context):
    data = load_data()
    user = get_user_data(data, update.effective_user.id)
    if not user["reminders"]:
        await update.message.reply_text("No reminders yet. Add one with /remind")
        return
    lines = [f"{i+1}. {r['text']} ({r['created']})" for i, r in enumerate(user["reminders"])]
    await update.message.reply_text("\n".join(lines))

async def expense(update, context):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /expense 12.50 lunch")
        return
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("First value must be a number, e.g. /expense 12.50 lunch")
        return
    note = " ".join(context.args[1:]) or "no note"
    data = load_data()
    user = get_user_data(data, update.effective_user.id)
    user["expenses"].append({"amount": amount, "note": note, "date": datetime.now().strftime("%Y-%m-%d")})
    save_data(data)
    await update.message.reply_text(f"Logged: {amount} - {note}")

async def list_expenses(update, context):
    data = load_data()
    user = get_user_data(data, update.effective_user.id)
    if not user["expenses"]:
        await update.message.reply_text("No expenses logged yet.")
        return
    total = sum(e["amount"] for e in user["expenses"])
    lines = [f"{e['date']}: {e['amount']} - {e['note']}" for e in user["expenses"]]
    lines.append(f"\nTotal: {total:.2f}")
    await update.message.reply_text("\n".join(lines))

async def unknown(update, context):
    await update.message.reply_text("I didn't understand that. Try /help")

from flask import Flask, request
import asyncio

flask_app = Flask(__name__)
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_cmd))
telegram_app.add_handler(CommandHandler("faq", faq))
telegram_app.add_handler(CommandHandler("remind", remind))
telegram_app.add_handler(CommandHandler("reminders", list_reminders))
telegram_app.add_handler(CommandHandler("expense", expense))
telegram_app.add_handler(CommandHandler("expenses", list_expenses))
telegram_app.add_handler(CommandHandler("mylocation", mylocation))
telegram_app.add_handler(CommandHandler("download", download))
telegram_app.add_handler(MessageHandler(filters.LOCATION, handle_location))
telegram_app.add_handler(MessageHandler(filters.COMMAND, unknown)
                         )

@flask_app.route("/", methods=["GET"])
def home():
    return "Bot is alive!"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        async with telegram_app:
            update = Update.de_json(request.get_json(force=True), telegram_app.bot)
            await telegram_app.process_update(update)
    asyncio.run(process())
    return "ok"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
