import os
from flask import Flask
from telegram import Bot
from events import fetch_new_events

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def send_notifications():
    """Cloud Function HTTP trigger to send notifications."""
    if not CHAT_ID:
        return "CHAT_ID not set", 400

    new_events = fetch_new_events()
    if not new_events:
        return "No new events", 200

    for event in new_events:
        message = f"🎟 *{event['event_Name']}*\n📍 {event['venue_Name']}, {event['city_Name']}\n📅 {event['event_Display_Date']}\n💰 {event['event_Price_Range']}\n🔗 [Buy Tickets]({event['event_Button_Text']})"
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

    return "Notifications Sent", 200
