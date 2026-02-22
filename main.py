import requests
from datetime import datetime
import pytz
import re
from playwright.sync_api import sync_playwright

BOT_TOKEN = "8080204943:AAHsR-QnuxS520DlaqN7IhVbgvCFzKuuTzE"
CHAT_ID = "-1001573667863"

RESTAURANTS = [
    {"name": "Супра Диди",   "id": "111112"},
    {"name": "Супра Меоре",  "id": "111114"},
    {"name": "Супра Романи", "id": "111113"},
]

EMAIL = "kren.irina@csg.ru"
PASSWORD = "Tornado9451!"


def get_date_str():
    tz = pytz.timezone("Asia/Vladivostok")
    today = datetime.now(tz)
    months = ["января","февраля","марта","апреля","мая","июня",
              "июля","августа","сентября","октября","ноября","декабря"]
    return f"{today.day} {months[today.month-1]}"


def login_playwright(page):
    """Login to Airesto with increased timeouts and multiple selector fallbacks"""
    page.goto("https://app.airesto.ru/login", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # Try multiple selectors for email field
    email_selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[placeholder*="mail"]',
        'input[placeholder*="логин"]',
        'input[placeholder*="Login"]',
        'form input:first-of-type',
    ]
    email_filled = False
    for sel in email_selectors:
        try:
            page.wait_for_selector(sel, timeout=5000, state="visible")
            page.fill(sel, EMAIL)
            email_filled = True
            break
        except:
            continue

    if not email_filled:
        # Last resort: fill all text inputs
        inputs = page.query_selector_all('input')
        for inp in inputs:
            t = inp.get_attribute('type') or 'text'
            if t in ('email', 'text', ''):
                inp.fill(EMAIL)
                break

    page.wait_for_timeout(500)

    # Password field
    pwd_selectors = [
        'input[type="password"]',
        'input[name="password"]',
        'input[placeholder*="парол"]',
    ]
    for sel in pwd_selectors:
        try:
            page.fill(sel, PASSWORD)
            break
        except:
            continue

    page.wait_for_timeout(500)

    # Click login button
    btn_selectors = [
        'button[type="submit"]',
        'button:has-text("Войти")',
        'button:has-text("Login")',
        'input[type="submit"]',
    ]
    for sel in btn_selectors:
        try:
            page.click(sel, timeout=3000)
            break
        except:
            continue

    # Wait for redirect after login
    page.wait_for_url("**airesto.ru/restaurant**", timeout=20000)
    page.wait_for_timeout(2000)


def take_screenshot_and_get_data(restaurant_id):
    screenshot_path = f"/tmp/screen_{restaurant_id}.png"
    hours_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        login_playwright(page)

        page.goto(
            f"https://app.airesto.ru/restaurant/{restaurant_id}/booking/list",
            wait_until="domcontentloaded",
            timeout=20000
        )
        page.wait_for_timeout(3000)

        # Click "Все" to show all bookings
        try:
            page.locator('text=Все').first.click(timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass

        # Parse hours data
        content = page.inner_text('body')
        pattern = r'(\d{2}:\d{2})\s+(\d+)\s*чел\s+(\d+)\s*штк'
        matches = re.findall(pattern, content)
        for hour, people, count in matches:
            hours_data[hour] = {"people": int(people), "count": int(count)}

        # Screenshot of the table area
        try:
            page.screenshot(path=screenshot_path, clip={
                "x": 260, "y": 160, "width": 1130, "height": 320
            })
        except:
            page.screenshot(path=screenshot_path)

        browser.close()

    return screenshot_path, hours_data


def build_message(restaurant_name, hours_data):
    date_str = get_date_str()
    lines = [f"\U0001f4ca <b>{date_str}. {restaurant_name}. Бронирования</b>\n"]
    for hour in sorted(hours_data.keys()):
        p = hours_data[hour]["people"]
        c = hours_data[hour]["count"]
        if c == 1:
            word = "бронь"
        elif 2 <= c <= 4:
            word = "брони"
        else:
            word = "броней"
        lines.append(f"С {hour} \u2014 {p} чел; {c} {word}")
    return "\n".join(lines)


def send_photo(photo_path, caption):
    with open(photo_path, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": f}
        )


def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    )


def main():
    for rest in RESTAURANTS:
        try:
            screenshot, hours_data = take_screenshot_and_get_data(rest["id"])
            message = build_message(rest["name"], hours_data)
            send_photo(screenshot, message)
            print(f"OK: {rest['name']}")
        except Exception as e:
            send_message(f"\u26a0\ufe0f Ошибка {rest['name']}: {e}")
            print(f"ERROR {rest['name']}: {e}")


if __name__ == "__main__":
    main()
