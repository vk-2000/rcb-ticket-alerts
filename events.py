from google.cloud import firestore
import os
import requests
import logging

db = firestore.Client()
API_URL = os.getenv("API_URL")

def get_seen_events():
    """Retrieve seen events from Firestore."""
    doc = db.collection("settings").document("seen_events").get()
    logging.info(f"Seen events: {doc.to_dict().get('event_ids', [])}")
    return set(doc.to_dict().get("event_ids", [])) if doc.exists else set()

def save_seen_events(event_ids):
    """Save seen events to Firestore."""
    db.collection("settings").document("seen_events").set({"event_ids": list(event_ids)}, merge=True)
    logging.info(f"Saved seen events: {list(event_ids)}")

def fetch_new_events():
    """Fetch new events & filter unseen ones."""
    seen_events = get_seen_events()
    response = requests.get(API_URL).json()
    new_events = []

    for event in response.get("result", []):
        event_id = f"{event['event_Group_Code']}-{event['event_Code']}"
        if event_id not in seen_events:
            new_events.append(event)
            seen_events.add(event_id)

    save_seen_events(seen_events)
    return new_events
