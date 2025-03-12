import os
import logging
import asyncio
from flask import Request
from telegram import Bot
from telegram.ext import Application, AIORateLimiter
from telegram.error import TelegramError
from events import fetch_new_events

# Configure logging
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Application.builder().token(TELEGRAM_BOT_TOKEN).rate_limiter(AIORateLimiter()).build()

async def send_message_async(chat_id, message):
    """Send a message asynchronously using Telegram API."""
    try:
        await app.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        logging.info(f"Sent notification for: {message[:30]}...")  # Log first 30 chars
    except TelegramError as e:
        logging.error(f"Failed to send message: {e}")

async def send_notifications_async():
    """Cloud Function HTTP trigger to send notifications asynchronously."""
    logging.info("Received request to send notifications.")

    if not TELEGRAM_CHAT_ID:
        logging.error("CHAT_ID environment variable is not set.")
        return "CHAT_ID not set", 400

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
        tasks.append(send_message_async(TELEGRAM_CHAT_ID, message))

    await asyncio.gather(*tasks)  # Run all message-sending tasks concurrently
    logging.info("All notifications sent successfully.")

    return "Notifications Sent", 200

def send_notifications(request: Request):
    """Entry point for the Cloud Function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(send_notifications_async())
