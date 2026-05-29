import asyncio
import feedparser
import requests
import random

from bs4 import BeautifulSoup
from difflib import SequenceMatcher

TOKEN = "8925579420:AAGyCsP_FNRMkO6YBNdSvR2Tzb7cIpdZyoE"
CHANNEL_ID = "-1004260226565"

RSS_FEEDS = [

    # Россия
    "https://lenta.ru/rss/news",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml",

    # ЧП / происшествия
    "https://www.mk.ru/rss/index.xml",
    "https://aif.ru/rss/all.php",
    "https://ren.tv/export/yandex-news.rss",
    "https://life.ru/xml/feed.xml",

    # Регионы
    "https://bloknot.ru/rss",
    "https://news.ru/rss/index.xml",
    "https://fedpress.ru/rss",
    "https://svpressa.ru/rss/all.xml",

    # Политика / события
    "https://iz.ru/xml/rss/all.xml",
    "https://ura.news/rss",

    # Экстренные новости
    "https://tvzvezda.ru/export/rss/news.xml",
    "https://vm.ru/rss/news",

    # Криминал / ДТП
    "https://www.interfax.ru/rss.asp",
    "https://www.kp.ru/rss/allsections.xml",

    # Дополнительные СМИ
    "https://www.fontanka.ru/fontanka.rss",
    "https://www.47news.ru/export/rss.xml",
    "https://www.ntv.ru/novosti/rss/",
    "https://www.vesti.ru/vesti.rss",
    "https://rg.ru/xml/index.xml",




    # Регионы / ЧП
    "https://www.e1.ru/text/rss.region.xml",
    "https://www.ngs.ru/text/rss.region.xml",
    "https://161.ru/text/rss.region.xml",
    "https://74.ru/text/rss.region.xml",
]

MIN_POST_INTERVAL = 600

MEMORY_FILE = "sent_news.txt"

sent_links = set()
sent_titles = []
recent_hashes = set()

category_stats = {}
city_stats = {}

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

CITIES = {

    "Москва": [
        "москв",
        "московск"
    ],

    "Санкт-Петербург": [
        "питер",
        "санкт-петерб",
        "спб"
    ],

    "Самара": [
        "самар"
    ],

    "Волгоград": [
        "волгогра"
    ],

    "Екатеринбург": [
        "екатеринбург",
        "екб"
    ],

    "Казань": [
        "казан"
    ],

    "Ставрополь": [
        "ставрополь",
        "минводы",
        "пятигорск",
        "кисловодск"
    ]
}


def load_memory():

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

    return None


def detect_city(text):

    text = text.lower()

    for city, keywords in CITIES.items():

        for kw in keywords:

            if kw in text:
                return city

    return None

def update_stats(category, city):

    if category:

        if category not in category_stats:
            category_stats[category] = 0

        category_stats[category] += 1

    if city:

        if city not in city_stats:
            city_stats[city] = 0

        city_stats[city] += 1


def clean_title(title):

    title = title.lower()

    bad_words = [

        "в россии",
        "в москве",
        "сегодня",
        "произошло",
        "случилось",
        "появилось",
        "сообщается",
        "стало известно",
        "опубликовано",
        "видео",
        "фото",
        "последствия",
        "подробности",
        "очевидцы",
        "экстренные службы",
        "на месте",
        ":",
        ",",
        ".",
        "!"
    ]

    for word in bad_words:

        title = title.replace(
            word,
            ""
        )

    return " ".join(title.split())

def make_news_hash(title):

    title = clean_title(title)

    words = title.split()

    # убираем короткие слова
    words = [
        word
        for word in words
        if len(word) > 3
    ]

    # сортируем
    words = sorted(words)

    # берём первые 6 слов
    return " ".join(words[:6])


def is_similar(title):

    title = clean_title(title)

    words1 = set(title.split())

    for old_title in sent_titles:

        old_title = clean_title(old_title)

        words2 = set(old_title.split())

        common_words = words1.intersection(words2)

        # если совпало много слов
        if len(common_words) >= 3:
            return True

        similarity = SequenceMatcher(
            None,
            title,
            old_title
        ).ratio()

        # очень жёсткий фильтр
        if similarity >= 0.82:
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

        selectors = [

            ("meta", "property", "og:image"),
            ("meta", "name", "twitter:image")
        ]

        for tag, attr, value in selectors:

            meta = soup.find(
                tag,
                attrs={
                    attr: value
                }
            )

            if (
                meta
                and meta.get("content")
            ):

                return meta["content"]

        # fallback обычных img

        images = soup.find_all("img")

        for img in images:

            src = img.get("src")

            if not src:
                continue

            if (
                "logo" in src
                or "icon" in src
            ):
                continue

            if src.startswith("//"):
                src = "https:" + src

            elif src.startswith("/"):

                domain = (
                    url.split("/")[0]
                    + "//"
                    + url.split("/")[2]
                )

                src = domain + src

            return src

    except Exception as e:

        print(
            "Ошибка фото:",
            e
        )

    return None

def ai_rewrite(title, category):

    text = title.strip()

    replacements = {

        "произошло": "случилось",
        "автомобиль": "машина",
        "транспортное средство": "авто",
        "мужчина": "человек",
        "женщина": "местная жительница",
        "в результате": "из-за",
        "совершил": "устроил",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    urgent_words = [

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
        for word in urgent_words
    ):

        text = (
            "⚡ "
            + text
        )

    return text


def make_hashtags(category, title):

    tags = ["#Новости"]

    if "🚗" in category:
        tags.append("#ДТП")

    if "🔥" in category:
        tags.append("#Пожар")

    if "☠️" in category:
        tags.append("#Криминал")

    if "💥" in category:
        tags.append("#Взрыв")

    return " ".join(tags)


def create_post(
    category,
    title,
    link,
    city=None
):

    hashtags = make_hashtags(
        category,
        title
    )

    city_tag = ""

    if city:
        city_tag = f" #{city}"

    text = f"""
{category}

📰 <b>{title}</b>

🔗 <a href="{link}">Источник</a>

{hashtags}{city_tag}
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

                if not any(
                    word in full_text.lower()
                    for word in HOT_WORDS
                ):
                    continue

                if any(
                    word in full_text.lower()
                    for word in BAD_WORDS
                ):
                    continue

                category = detect_category(
                    full_text
                )

                if not category:
                    continue

                news_hash = make_news_hash(title)

                if (
                        is_similar(title)
                        or news_hash in recent_hashes
                ):
                    print(
                        "⛔ Дубль:",
                        title
                    )

                    continue

                save_memory(link)

                photo = get_image_from_article(
                    link
                )

                title = ai_rewrite(
                    title,
                    category
                )

                city = detect_city(title)

                update_stats(
                    category,
                    city
                )

                post = create_post(
                    category,
                    title,
                    link,
                    city
                )

                sent_links.add(link)
                sent_titles.append(title)
                recent_hashes.add(news_hash)

                news.append(
                    (photo, post)
                )

        except Exception as e:

            print("Ошибка RSS:", e)

    return news


def create_digest(
    news_list,
    max_items=10
):

    if not news_list:
        return None

    digest_text = (
        "📰 <b>Главное "
        "за последний час:</b>\n\n"
    )

    count = 0

    for _, post in news_list:

        first_line = (
            post.strip().split("\n")[2]
        )

        digest_text += (
            f"• {first_line}\n"
        )

        count += 1

        if count >= max_items:
            break

    digest_text += (
        "\n#Сводка #Новости #Россия"
    )

    return digest_text

def create_stats_report():

    text = "📊 <b>Статистика новостей:</b>\n\n"

    text += "📰 По категориям:\n"

    for category, count in category_stats.items():

        text += f"{category} — {count}\n"

    text += "\n🏙 По городам:\n"

    for city, count in city_stats.items():

        text += f"#{city} — {count}\n"

    text += "\n#Статистика #Новости"

    return text


async def main():

    load_memory()

    print(
        "🚨 ЧП бот запущен"
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

            all_news = news

            for photo, post in all_news:

                send_post(photo, post)

                print(
                    "✅ Новость опубликована"
                )

                print(
                    f"⏰ Следующий пост "
                    f"через "
                    f"{MIN_POST_INTERVAL // 60} "
                    f"минут"
                )

                await asyncio.sleep(
                    MIN_POST_INTERVAL
                )

            digest = create_digest(
                all_news,
                max_items=10
            )

            if digest:
                send_post(
                    None,
                    digest
                )

                print(
                    "📝 Опубликована сводка"
                )

                # stats_post = create_stats_report()

                # send_post(
                #     None,
                #     stats_post
                # )

                # print(
                #     "📊 Статистика опубликована"
                # )

        except Exception as e:

            print(
                "Общая ошибка:",
                e
            )

            await asyncio.sleep(30)


asyncio.run(main())