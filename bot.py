import asyncio
import feedparser
import requests

from bs4 import BeautifulSoup
from difflib import SequenceMatcher

TOKEN = "8925579420:AAGyCsP_FNRMkO6YBNdSvR2Tzb7cIpdZyoE"
CHANNEL_ID = "-1004260226565"

RSS_FEEDS = [
    "https://lenta.ru/rss/news",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml"
]

MIN_POST_INTERVAL = 600

MEMORY_FILE = "sent_news.txt"

sent_links = set()
sent_titles = []

CATEGORIES = {

    "🚗 ДТП": [
        "дтп",
        "авария",
        "столкнов",
        "машин",
        "автомоб"
    ],

    "🔥 Пожар": [
        "пожар",
        "горел",
        "огонь",
        "возгорание"
    ],

    "☠️ Криминал": [
        "убил",
        "убийство",
        "зарезал",
        "труп",
        "застрел"
    ],

    "💥 Взрыв": [
        "взрыв",
        "детонация",
        "бомба"
    ],

    "🚨 ЧП": [
        "происшествие",
        "катастроф",
        "нападение",
        "обрушение"
    ]
}


def load_memory():

    try:

        with open(MEMORY_FILE, "r", encoding="utf-8") as file:

            for line in file:

                line = line.strip()

                if line:

                    sent_links.add(line)

    except:

        pass


def save_memory(link):

    with open(
        MEMORY_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(link + "\n")


def detect_category(text):

    text = text.lower()

    for category, words in CATEGORIES.items():

        for word in words:

            if word in text:
                return category

    return None


def clean_title(title):

    title = title.lower()

    bad_words = [
        "в россии",
        "в москве",
        "сегодня",
        "произошло"
    ]

    for word in bad_words:

        title = title.replace(word, "")

    return title.strip()


def is_similar(title):

    title = clean_title(title)

    words1 = set(title.split())

    for old_title in sent_titles:

        old_title = clean_title(old_title)

        words2 = set(old_title.split())

        common_words = words1.intersection(words2)

        if len(common_words) >= 2:
            return True

        similarity = SequenceMatcher(
            None,
            title,
            old_title
        ).ratio()

        if similarity > 0.50:
            return True

    return False


def get_image_from_article(url):

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        meta = soup.find(
            "meta",
            property="og:image"
        )

        if meta and meta.get("content"):

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

    try:

        if photo:

            url = (
                f"https://api.telegram.org/"
                f"bot{TOKEN}/sendPhoto"
            )

            data = {
                "chat_id": CHANNEL_ID,
                "photo": photo,
                "caption": text,
                "parse_mode": "HTML"
            }

        else:

            url = (
                f"https://api.telegram.org/"
                f"bot{TOKEN}/sendMessage"
            )

            data = {
                "chat_id": CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML"
            }

        response = requests.post(
            url,
            data=data,
            timeout=30
        )

        print(response.text)

    except Exception as e:

        print("Ошибка отправки:", e)


def get_news():

    news = []

    for feed_url in RSS_FEEDS:

        try:

            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:10]:

                link = entry.link
                title = entry.title

                if link in sent_links:
                    continue

                full_text = (
                    f"{title} {link}"
                )

                category = detect_category(
                    full_text
                )

                if not category:
                    continue

                if is_similar(title):

                    print(
                        "⛔ Дубль:",
                        title
                    )

                    continue

                sent_links.add(link)
                sent_titles.append(title)

                save_memory(link)

                photo = get_image_from_article(
                    link
                )

                post = create_post(
                    category,
                    title,
                    link
                )

                news.append(
                    (photo, post)
                )

        except Exception as e:

            print("Ошибка RSS:", e)

    return news


async def main():

    load_memory()

    print(
        "🚨 ЧП бот "
        "с памятью запущен"
    )

    while True:

        try:

            news = get_news()

            if not news:

                print(
                    "📰 Новых новостей нет"
                )

                await asyncio.sleep(120)

                continue

            print(
                f"📰 Найдено новостей: "
                f"{len(news)}"
            )

            for photo, post in news:

                send_post(photo, post)

                print(
                    "✅ Новость опубликована"
                )

                await asyncio.sleep(
                    MIN_POST_INTERVAL
                )

        except Exception as e:

            print(
                "Общая ошибка:",
                e
            )

            await asyncio.sleep(30)


asyncio.run(main())