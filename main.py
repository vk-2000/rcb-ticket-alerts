import os
import logging
import functions_framework
from flask import Request
from telegram import Update
from telegram.ext import Application, CommandHandler, AIORateLimiter
from telegram.error import TelegramError
from google.cloud import firestore
import asyncio
from events import fetch_new_events

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize Firestore
db = firestore.Client()

# Initialize Telegram bot
app = Application.builder().token(TELEGRAM_BOT_TOKEN).rate_limiter(AIORateLimiter()).build()

# ------------------- TELEGRAM COMMAND HANDLERS -------------------

async def start(update: Update, context):
    """Send welcome message and instructions."""
    await update.message.reply_text("👋 Welcome! Use /subscribe to receive event notifications.")

async def subscribe(update: Update, context):
    """Subscribe a user for event notifications."""
    chat_id = str(update.message.chat_id)
    user_ref = db.collection("telegram_users").document(chat_id)
    user_data = user_ref.get()

    if user_data.exists and user_data.to_dict().get("subscribed", False):
        await update.message.reply_text("🔔 You are already subscribed!")
        return

    user_ref.set({"subscribed": True}, merge=True)
    await update.message.reply_text("✅ You are now subscribed to event notifications!")

async def unsubscribe(update: Update, context):
    """Unsubscribe a user from notifications."""
    chat_id = str(update.message.chat_id)
    user_ref = db.collection("telegram_users").document(chat_id)
    user_data = user_ref.get()

    if not user_data.exists or not user_data.to_dict().get("subscribed", False):
        await update.message.reply_text("ℹ️ You are not subscribed!")
        return

    user_ref.set({"subscribed": False}, merge=True)
    await update.message.reply_text("❌ You have been unsubscribed.")

async def list_events(update: Update, context):
    """Fetch and display the latest events."""
    new_events = fetch_new_events()

    if not new_events:
        await update.message.reply_text("📭 No new events at the moment.")
        return

    for event in new_events[:5]:  # Limit to latest 5 events
        message = (
            f"🎟 *{event['event_Name']}*\n"
            f"📍 {event['venue_Name']}, {event['city_Name']}\n"
            f"📅 {event['event_Display_Date']}\n"
            f"💰 {event['event_Price_Range']}\n"
            f"🔗 [Buy Tickets](https://shop.royalchallengers.com/ticket/{event['event_Code']})"
        )
        await update.message.reply_text(message, parse_mode="Markdown")

# Register command handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("subscribe", subscribe))
app.add_handler(CommandHandler("unsubscribe", unsubscribe))
app.add_handler(CommandHandler("list_events", list_events))

# ------------------- EVENT NOTIFICATIONS -------------------

async def send_message_async(chat_id, message):
    """Send a Telegram message asynchronously."""
    try:
        await app.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logging.info(f"Sent notification to {chat_id}")
    except TelegramError as e:
        logging.error(f"Failed to send message to {chat_id}: {e}")

async def send_notifications_async():
    """Fetch new events and send notifications to subscribed users."""
    logging.info("Checking for new events...")

    new_events = fetch_new_events()
    if not new_events:
        logging.info("No new events to notify.")
        return "No new events", 200

    subscribers = db.collection("telegram_users").where("subscribed", "==", True).stream()
    chat_ids = [doc.id for doc in subscribers]

    if not chat_ids:
        logging.info("No subscribed users to notify.")
        return "No subscribers", 200

    tasks = []
    for event in new_events:
        message = (
            f"🎟 *{event['event_Name']}*\n"
            f"📍 {event['venue_Name']}, {event['city_Name']}\n"
            f"📅 {event['event_Display_Date']}\n"
            f"💰 {event['event_Price_Range']}\n"
            f"🔗 [Buy Tickets](https://shop.royalchallengers.com/ticket/{event['event_Code']})"
        )
        for chat_id in chat_ids:
            tasks.append(send_message_async(chat_id, message))

    await asyncio.gather(*tasks)
    logging.info("All notifications sent.")

    return "Notifications Sent", 200

# ------------------- TELEGRAM WEBHOOK HANDLER -------------------

async def telegram_webhook_async(request: Request):
    """Process incoming Telegram webhook updates asynchronously."""
    update = Update.de_json(request.get_json(), app.bot)
    print(f"Received update: {update}")
    logging.info(f"Received update: {update}")
    await app.process_update(update)
    return "OK", 200

@functions_framework.http
def telegram_webhook(request: Request):
    """Process incoming Telegram webhook updates."""
    if request.method != "POST":
        return "Invalid request", 405

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(telegram_webhook_async(request))