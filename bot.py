import asyncio
import feedparser
import requests

from bs4 import BeautifulSoup

TOKEN = "8925579420:AAGyCsP_FNRMkO6YBNdSvR2Tzb7cIpdZyoE"
CHANNEL_ID = "-1004260226565"

RSS_FEEDS = [
    "https://lenta.ru/rss/news",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml"
]

sent = set()

CATEGORIES = {

    "🚗 ДТП": [
        "дтп",
        "авария",
        "столкнов",
        "машин"
    ],

    "🔥 Пожар": [
        "пожар",
        "горел",
        "огонь"
    ],

    "☠️ Убийство": [
        "убил",
        "убийство",
        "зарезал",
        "труп"
    ],

    "💥 Взрыв": [
        "взрыв",
        "детонация",
        "бомба"
    ],

    "🚨 ЧП": [
        "происшествие",
        "нападение",
        "катастроф"
    ]
}


def detect_category(text):

    text = text.lower()

    for category, words in CATEGORIES.items():

        for word in words:

            if word in text:
                return category

    return None


def get_image_from_article(url):

    try:

        response = requests.get(url, timeout=10)

        soup = BeautifulSoup(response.text, "html.parser")

        meta = soup.find("meta", property="og:image")

        if meta:
            return meta["content"]

    except:
        return None

    return None


def create_post(category, title, link):

    text = f"""
{category}

📰 <b>{title}</b>

🔗 <a href="{link}">Читать подробнее</a>

#Россия #Новости
"""

    return text


def send_post(photo, text):

    if photo:

        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

        data = {
            "chat_id": CHANNEL_ID,
            "photo": photo,
            "caption": text,
            "parse_mode": "HTML"
        }

    else:

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        data = {
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }

    response = requests.post(url, data=data, timeout=30)

    print(response.text)


def get_news():

    news = []

    for feed_url in RSS_FEEDS:

        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:

            if entry.link in sent:
                continue

            title = entry.title
            link = entry.link

            full_text = f"{title} {link}"

            category = detect_category(full_text)

            if not category:
                continue

            sent.add(entry.link)

            photo = get_image_from_article(link)

            post = create_post(category, title, link)

            news.append((photo, post))

    return news


async def main():

    print("🚨 ЧП бот с реальными фото запущен")

    while True:

        try:

            news = get_news()

            for photo, post in news:

                send_post(photo, post)

                print("✅ Новость опубликована")

                await asyncio.sleep(5)

            await asyncio.sleep(60)

        except Exception as e:

            print("Ошибка:", e)

            await asyncio.sleep(15)


asyncio.run(main())