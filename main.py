import requests
from datetime import datetime
import pytz

BOT_TOKEN = "8080204943:AAHsR-QnuxS520DlaqN7IhVbgvCFzKuuTzE"
CHAT_ID = "-1001573667863"

RESTAURANTS = [
    {"name": "Супра Меоре",  "id": "111114"},
    {"name": "Супра Диди",   "id": "111112"},
    {"name": "Супра Романи", "id": "111113"},
]

EMAIL = "kren.irina@csg.ru"
PASSWORD = "Tornado9451!"

BASE_URL = "https://app.airesto.ru"


def get_today_str():
    tz = pytz.timezone("Asia/Vladivostok")
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d"), now.strftime("%d %B %Y")


def login():
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    resp = session.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        token = data.get("token") or data.get("access_token") or data.get("data", {}).get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
    # fallback: try form login
    resp2 = session.post(
        f"{BASE_URL}/api/v1/auth/signin",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    if resp2.status_code == 200:
        data2 = resp2.json()
        token = data2.get("token") or data2.get("access_token") or data2.get("data", {}).get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def get_bookings(session, restaurant_id, date_str):
    """Try multiple API endpoints to get bookings for today."""
    endpoints = [
        f"{BASE_URL}/api/v1/restaurant/{restaurant_id}/booking/list?date={date_str}",
        f"{BASE_URL}/api/v1/restaurant/{restaurant_id}/bookings?date={date_str}",
        f"{BASE_URL}/api/v1/booking/list?restaurant_id={restaurant_id}&date={date_str}",
    ]
    for url in endpoints:
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                # unwrap data
                if isinstance(data, dict):
                    items = data.get("data") or data.get("bookings") or data.get("items") or []
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                if items:
                    return items
        except Exception:
            continue
    return []


def format_bookings(bookings, date_label):
    """Group bookings by time slot, output text."""
    from collections import defaultdict
    slots = defaultdict(list)
    for b in bookings:
        # extract time — try common field names
        time_val = (
            b.get("time") or b.get("booking_time") or
            b.get("start_time") or b.get("datetime") or
            b.get("date") or ""
        )
        # extract guests count
        guests = (
            b.get("guests") or b.get("persons") or
            b.get("guest_count") or b.get("count") or 0
        )
        # parse time to HH:MM
        try:
            if "T" in str(time_val):
                t = datetime.fromisoformat(str(time_val).replace("Z", "+00:00"))
                tz = pytz.timezone("Asia/Vladivostok")
                t = t.astimezone(tz)
                slot_key = t.strftime("%H:%M")
            elif ":" in str(time_val):
                slot_key = str(time_val)[:5]
            else:
                slot_key = "??"
        except Exception:
            slot_key = "??"
        slots[slot_key].append(int(guests))

    if not slots:
        return None

    lines = [date_label, "Бронирования"]
    for slot in sorted(slots.keys()):
        total_guests = sum(slots[slot])
        count = len(slots[slot])
        noun = "бронь" if count == 1 else ("брони" if 2 <= count <= 4 else "броней")
        lines.append(f"С {slot} — {total_guests} чел; {count} {noun}")
    return "\n".join(lines)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=30)
    return resp.status_code == 200


def main():
    date_str, date_label = get_today_str()
    session = login()

    for rest in RESTAURANTS:
        bookings = get_bookings(session, rest["id"], date_str)
        if bookings:
            text = format_bookings(bookings, date_label)
            if text:
                msg = f"{rest['name']}\n{text}"
            else:
                msg = f"{rest['name']}\n{date_label}\nНет бронирований"
        else:
            msg = f"{rest['name']}\n{date_label}\nНет бронирований (или ошибка API)"
        send_telegram(msg)
        print(msg)
        print("---")


if __name__ == "__main__":
    main()
