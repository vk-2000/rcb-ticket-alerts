import os
import logging
import asyncio
from flask import Request
from telegram import Update
from telegram.ext import Application, AIORateLimiter, CommandHandler, CallbackContext
from telegram.error import TelegramError
from google.cloud import firestore
from events import fetch_new_events

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load Telegram token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize Telegram bot
app = Application.builder().token(TELEGRAM_BOT_TOKEN).rate_limiter(AIORateLimiter()).build()

# Initialize Firestore
db = firestore.Client()

### 🔹 User Subscription Handlers

async def subscribe(update: Update, context: CallbackContext):
    """Subscribe the user to notifications."""
    chat_id = str(update.message.chat_id)
    
    # Set user as subscribed in Firestore
    db.collection("telegram_users").document(chat_id).set({"subscribed": True}, merge=True)
    
    await update.message.reply_text("✅ You are now subscribed to event notifications!")

async def unsubscribe(update: Update, context: CallbackContext):
    """Unsubscribe the user from notifications."""
    chat_id = str(update.message.chat_id)
    
    # Set user as unsubscribed in Firestore
    db.collection("telegram_users").document(chat_id).set({"subscribed": False}, merge=True)
    
    await update.message.reply_text("❌ You have been unsubscribed from notifications.")

### 🔹 Notification Sending

async def send_message_async(chat_id, message):
    """Send a message asynchronously using Telegram API."""
    try:
        await app.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logging.info(f"Sent notification to {chat_id}: {message[:30]}...")
    except TelegramError as e:
        logging.error(f"Failed to send message to {chat_id}: {e}")

async def send_notifications_async():
    """Cloud Function HTTP trigger to send notifications asynchronously."""
    logging.info("Received request to send notifications.")

    # Fetch all subscribed users
    users_ref = db.collection("telegram_users").where("subscribed", "==", True)
    docs = users_ref.stream()
    
    chat_ids = [doc.id for doc in docs]  # Firestore doc IDs are chat IDs
    if not chat_ids:
        logging.warning("No subscribed users found.")
        return "No users to notify", 200

    # Fetch new events
    new_events = fetch_new_events()
    if not new_events:
        logging.info("No new events found.")
        return "No new events", 200

    tasks = []
    for event in new_events:
        message = (
            f"🎟 *{event['event_Name']}*\n"
            f"📍 {event['venue_Name']}, {event['city_Name']}\n"
            f"📅 {event['event_Display_Date']}\n"
            f"💰 {event['event_Price_Range']}\n"
            f"🔗 [Buy Tickets](https://shop.royalchallengers.com/ticket/{event['event_Code']})"
        )

        # Send message to all subscribed chat IDs
        for chat_id in chat_ids:
            tasks.append(send_message_async(chat_id, message))

    await asyncio.gather(*tasks)  # Send messages concurrently
    logging.info("All notifications sent successfully.")

    return "Notifications Sent", 200

def send_notifications(request: Request):
    """Entry point for the Cloud Function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(send_notifications_async())

### 🔹 Register Commands
app.add_handler(CommandHandler("subscribe", subscribe))
app.add_handler(CommandHandler("unsubscribe", unsubscribe))
