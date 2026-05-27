import asyncio
import random
import feedparser
import requests

TOKEN = "8925579420:AAGyCsP_FNRMkO6YBNdSvR2Tzb7cIpdZyoE"
CHANNEL_ID = "-1004260226565"

RSS_FEEDS = [
    "https://lenta.ru/rss/news",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml"
]

sent = set()

CATEGORIES = {

    "🚗 ДТП": {
        "words": [
            "дтп",
            "авария",
            "столкнов",
            "машин"
        ],

        "photo": "https://images.unsplash.com/photo-1503376780353-7e6692767b70"
    },

    "🔥 Пожар": {
        "words": [
            "пожар",
            "горел",
            "огонь",
            "возгорание"
        ],

        "photo": "https://images.unsplash.com/photo-1516728778615-2d590ea1856b"
    },

    "☠️ Убийство": {
        "words": [
            "убил",
            "убийство",
            "зарезал",
            "труп"
        ],

        "photo": "https://images.unsplash.com/photo-1517841905240-472988babdf9"
    },

    "💥 Взрыв": {
        "words": [
            "взрыв",
            "детонация",
            "бомба"
        ],

        "photo": "https://images.unsplash.com/photo-1499092346589-b9b6be3e94b2"
    },

    "🚨 ЧП": {
        "words": [
            "происшествие",
            "катастроф",
            "нападение",
            "обрушение"
        ],

        "photo": "https://images.unsplash.com/photo-1521295121783-8a321d551ad2"
    }
}

AI_PHRASES = [
    "По предварительным данным,",
    "Как сообщают источники,",
    "Стало известно, что",
    "По имеющейся информации,",
    "Очевидцы сообщают,"
]


def detect_category(text):

    text = text.lower()

    for category, data in CATEGORIES.items():

        for word in data["words"]:

            if word in text:
                return category

    return None


def ai_rewrite(title):

    phrase = random.choice(AI_PHRASES)

    title = title.replace("В России", "")
    title = title.replace("в России", "")

    rewritten = f"{phrase} {title.lower()}."

    rewritten = rewritten.capitalize()

    return rewritten


def create_post(category, title, link):

    rewritten = ai_rewrite(title)

    text = f"""
{category}

📰 <b>{rewritten}</b>

🔗 <a href="{link}">Читать подробнее</a>

#Россия #Новости
"""

    return text


def send_post(category, text):

    photo = CATEGORIES[category]["photo"]

    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

    data = {
        "chat_id": CHANNEL_ID,
        "photo": photo,
        "caption": text,
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

            post = create_post(category, title, link)

            news.append((category, post))

    return news


async def main():

    print("🤖 AI ЧП бот запущен")

    while True:

        try:

            news = get_news()

            for category, post in news:

                send_post(category, post)

                print("✅ AI новость опубликована")

                await asyncio.sleep(5)

            await asyncio.sleep(60)

        except Exception as e:

            print("Ошибка:", e)

            await asyncio.sleep(15)


asyncio.run(main())