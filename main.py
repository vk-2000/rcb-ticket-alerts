import os
import logging
from flask import Request
from telegram import Bot
from events import fetch_new_events

# Configure logging
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def send_notifications(request: Request):
    """Cloud Function HTTP trigger to send notifications."""
    logging.info("Received request to send notifications.")

    if not TELEGRAM_CHAT_ID:
        logging.error("CHAT_ID environment variable is not set.")
        return "CHAT_ID not set", 400

    new_events = fetch_new_events()
    if not new_events:
        logging.info("No new events found.")
        return "No new events", 200

    for event in new_events:
        message = (
            f"🎟 *{event['event_Name']}*\n"
            f"📍 {event['venue_Name']}, {event['city_Name']}\n"
            f"📅 {event['event_Display_Date']}\n"
            f"💰 {event['event_Price_Range']}\n"
            f"🔗 [Buy Tickets]({event['event_Button_Text']})"
        )
        try:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
            logging.info(f"Sent notification for event: {event['event_Name']}")
        except Exception as e:
            logging.error(f"Failed to send message for {event['event_Name']}: {e}")

    logging.info("All notifications sent successfully.")
    return "Notifications Sent", 200
