import requests
import json
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = os.getenv("API_URL")

bot = Bot(token=BOT_TOKEN)
seen_events_file = "seen_events.json"

def get_events():
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()
        return data.get("result", [])
    return []

def load_seen_events():
    try:
        with open(seen_events_file, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_seen_events(events):
    with open(seen_events_file, "w") as f:
        json.dump(list(events), f)

async def send_notification(event):
    message = f"🎟 New Event: {event['event_Name']}\n📍 Venue: {event['venue_Name']}, {event['city_Name']}\n📅 Date: {event['event_Display_Date']}\n💰 Price: {event['event_Price_Range']}\n🔗 [Buy Tickets]({event['event_Banner']})"
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

async def main():
    seen_events = load_seen_events()
    events = get_events()
    print(events)
    new_events = [e for e in events if str(e["event_Code"]) not in seen_events]

    for event in new_events:
        await send_notification(event)
        seen_events.add(str(event["event_Code"]))

    save_seen_events(seen_events)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
