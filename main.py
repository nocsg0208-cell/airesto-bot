import requests
from datetime import datetime
import pytz
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


def login_and_get_page(page):
    page.goto("https://app.airesto.ru/login")
    page.wait_for_selector('input[type="email"]', timeout=10000)
    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button:has-text("Войти")')
    page.wait_for_url("**/restaurant/**", timeout=15000)


def take_screenshot_and_get_data(restaurant_id):
    screenshot_path = f"/tmp/screen_{restaurant_id}.png"
    hours_data = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        login_and_get_page(page)

        page.goto(f"https://app.airesto.ru/restaurant/{restaurant_id}/booking/list")
        page.wait_for_timeout(3000)

        # Кликаем "Все" чтобы показать все брони
        try:
            all_btn = page.locator('text=Все').first
            all_btn.click(timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass

        # Собираем данные по часам из таблицы
        import re
        content = page.inner_text('body')
        pattern = r'(\d{2}:\d{2})\s+(\d+)\s*чел\s+(\d+)\s*штк'
        matches = re.findall(pattern, content)
        for hour, people, count in matches:
            hours_data[hour] = {"people": int(people), "count": int(count)}

        # Скриншот таблицы
        try:
            table_area = page.locator('[class*="timeline"], [class*="booking-table"], .table-hours').first
            table_area.screenshot(path=screenshot_path)
        except:
            # Если не нашли блок — скриншот всей верхней части
            page.screenshot(path=screenshot_path, clip={
                "x": 260, "y": 170, "width": 1140, "height": 310
            })

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
