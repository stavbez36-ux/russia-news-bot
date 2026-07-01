import asyncio
import feedparser
import requests
import hashlib

from bs4 import BeautifulSoup
from difflib import SequenceMatcher


import os

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")


RSS_FEEDS = [

    # Россия
   
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml",

    # ЧП
    "https://www.mk.ru/rss/index.xml",
    "https://aif.ru/rss/all.php",
    "https://ren.tv/export/yandex-news.rss",
    

    # Регионы
    "https://bloknot.ru/rss",
    "https://news.ru/rss/index.xml",
    "https://fedpress.ru/rss",
    "https://svpressa.ru/rss/all.xml",

    # Политика
    "https://iz.ru/xml/rss/all.xml",
    "https://ura.news/rss",
    "https://rg.ru/xml/index.xml",

    # Экстренные
    "https://tvzvezda.ru/export/rss/news.xml",
    "https://vm.ru/rss/news",

    # Криминал
    "https://www.interfax.ru/rss.asp",
    "https://www.kp.ru/rss/allsections.xml",

    # СМИ
    "https://www.fontanka.ru/fontanka.rss",
    "https://www.47news.ru/export/rss.xml",
    "https://www.ntv.ru/novosti/rss/",
    "https://www.vesti.ru/vesti.rss",
    

    # Регионы
    "https://www.e1.ru/text/rss.region.xml",
    "https://www.ngs.ru/text/rss.region.xml",
    "https://161.ru/text/rss.region.xml",
    "https://74.ru/text/rss.region.xml",
]


MIN_POST_INTERVAL = 600
CHECK_INTERVAL = 120

MEMORY_FILE = "sent_news.txt"

sent_links = set()
sent_hashes = set()
sent_titles = []


BAD_WORDS = [

    "реклама",
    "скидк",
    "маркет",
    "рейтинг",
    "тест",
    "обзор",
    "что лучше",
    "советы",
    "рецепт"
]


HOT_WORDS = [

    "погиб",
    "умер",
    "убил",
    "убийство",
    "теракт",
    "взрыв",
    "пожар",
    "эвакуация",
    "обрушение",
    "нападение",
    "стрельба",
    "дрон",
    "бпла",
    "беспилотник",
    "ранен",
    "пострадал",
    "чп",
    "дтп",
    "авария",
    "катастрофа"
]


CATEGORIES = {

    "🚗 ДТП": [
        "дтп",
        "авария",
        "столкнов",
        "машин",
        "автомоб",
        "сбил"
    ],

    "🔥 Пожар": [
        "пожар",
        "горел",
        "огонь",
        "возгорание",
        "дым"
    ],

    "☠️ Криминал": [
        "убил",
        "убийство",
        "зарезал",
        "труп",
        "застрел",
        "напал",
        "избил"
    ],

    "💥 Взрыв": [
        "взрыв",
        "детонация",
        "бомба",
        "хлопок"
    ],

    "🌊 Катастрофа": [
        "обрушение",
        "затопление",
        "ураган",
        "землетрясение"
    ],

    "🚨 ЧП": [
        "происшествие",
        "катастроф",
        "нападение"
    ]
}


def load_memory():

    global sent_links

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

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

    return "🚨 ЧП"


def clean_title(title):

    title = title.lower()

    garbage = [

        "видео",
        "фото",
        "сегодня",
        "последствия",
        "подробности",
        "очевидцы",
        "экстренные службы",
        "на месте",
        "стало известно",
        "сообщается",
        "произошло",
        "случилось",
        ":",
        ",",
        ".",
        "!"
    ]

    for word in garbage:

        title = title.replace(word, "")

    return " ".join(title.split())


def make_news_hash(title):

    title = clean_title(title)

    words = title.split()

    words = [

        word
        for word in words
        if len(word) > 3
    ]

    important = words[:6]

    text = " ".join(important)

    return hashlib.md5(
        text.encode("utf-8")
    ).hexdigest()


def is_similar(title):

    global sent_titles

    title = clean_title(title)

    for old_title in sent_titles:

        similarity = SequenceMatcher(
            None,
            title,
            old_title
        ).ratio()

        if similarity >= 0.80:
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

        if (
            meta
            and meta.get("content")
        ):
            return meta["content"]

    except:
        pass

    return None


def ai_rewrite(title):

    text = title.strip()

    replacements = {

        "произошло": "случилось",
        "автомобиль": "машина",
        "транспортное средство": "авто",
        "в результате": "из-за",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    urgent = [

        "погиб",
        "теракт",
        "взрыв",
        "стрельба",
        "убийство",
        "дрон",
        "бпла"
    ]

    if any(
        word in text.lower()
        for word in urgent
    ):
        text = "⚡ " + text

    return text


def create_post(
    category,
    title,
    link
):

    hashtags = "#Новости"

    if "🚗" in category:
        hashtags += " #ДТП"

    if "🔥" in category:
        hashtags += " #Пожар"

    if "☠️" in category:
        hashtags += " #Криминал"

    if "💥" in category:
        hashtags += " #Взрыв"

    text = f"""
{category}

📰 <b>{title}</b>

🔗 <a href="{link}">Источник</a>

{hashtags}
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

    global sent_links
    global sent_hashes
    global sent_titles

    news = []

    local_hashes = set()

    for feed_url in RSS_FEEDS:

        try:

            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:10]:

                try:

                    link = entry.link.strip()
                    title = entry.title.strip()

                    if not link or not title:
                        continue

                    # уже отправляли ссылку
                    if link in sent_links:
                        continue

                    full_text = (
                        f"{title} {link}"
                    ).lower()

                    # фильтр горячих новостей
                    if not any(
                        word in full_text
                        for word in HOT_WORDS
                    ):
                        continue

                    # мусор
                    if any(
                        word in full_text
                        for word in BAD_WORDS
                    ):
                        continue

                    # hash новости
                    news_hash = make_news_hash(
                        title
                    )

                    # главный антидубль
                    if (
                        news_hash in sent_hashes
                        or news_hash in local_hashes
                    ):

                        print(
                            "⛔ Дубль HASH:",
                            title
                        )

                        continue

                    # проверка похожести
                    if is_similar(title):

                        print(
                            "⛔ Дубль TEXT:",
                            title
                        )

                        continue

                    category = detect_category(
                        full_text
                    )

                    final_title = ai_rewrite(
                        title
                    )

                    photo = get_image_from_article(
                        link
                    )

                    post = create_post(
                        category,
                        final_title,
                        link
                    )

                    # сохраняем
                    sent_links.add(link)

                    sent_hashes.add(
                        news_hash
                    )

                    local_hashes.add(
                        news_hash
                    )

                    sent_titles.append(
                        clean_title(title)
                    )

                    save_memory(link)

                    # защита памяти
                    if len(sent_titles) > 2000:
                        sent_titles = sent_titles[-1000:]

                    if len(sent_hashes) > 5000:
                        sent_hashes = set(
                            list(sent_hashes)[-2500:]
                        )

                    news.append(
                        (photo, post)
                    )

                except Exception as e:

                    print(
                        "Ошибка entry:",
                        e
                    )

        except Exception as e:

            print(
                "Ошибка RSS:",
                e
            )

    return news


async def main():

    load_memory()

    print(
        "🚨 Бот запущен"
    )

    while True:

        try:

            news = get_news()

            if not news:

                print(
                    "📰 Новых новостей нет"
                )

                await asyncio.sleep(
                    CHECK_INTERVAL
                )

                continue

            print(
                f"📰 Найдено новостей: {len(news)}"
            )

            for photo, post in news:

                send_post(
                    photo,
                    post
                )

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
