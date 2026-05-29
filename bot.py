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
    "https://tass.ru/rss/v2.xml",
    "https://www.mk.ru/rss/index.xml",
    "https://aif.ru/rss/all.php",
    "https://ren.tv/export/yandex-news.rss",
    "https://life.ru/xml/feed.xml",
    "https://bloknot.ru/rss",
    "https://news.ru/rss/index.xml",
    "https://fedpress.ru/rss",
    "https://svpressa.ru/rss/all.xml",
    "https://iz.ru/xml/rss/all.xml",
    "https://www.gazeta.ru/export/rss/lenta.xml",
    "https://ura.news/rss",
    "https://tvzvezda.ru/export/rss/news.xml",
    "https://vm.ru/rss/news",
    "https://www.interfax.ru/rss.asp",
    "https://www.kp.ru/rss/allsections.xml",
    "https://www.fontanka.ru/fontanka.rss",
    "https://www.47news.ru/export/rss.xml",
    "https://www.ntv.ru/novosti/rss/",
    "https://www.vesti.ru/vesti.rss",
    "https://rg.ru/xml/index.xml",
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

BAD_WORDS = [
    "реклама", "скидк", "маркет", "рейтинг", "тест",
    "обзор", "что лучше", "советы", "рецепт"
]

HOT_WORDS = [
    "погиб", "умер", "убил", "убийство", "теракт",
    "взрыв", "пожар", "эвакуация", "обрушение",
    "нападение", "стрельба", "дрон", "бпла", "беспилотник",
    "ранен", "пострадал", "чп", "дтп", "авария", "катастрофа"
]

CATEGORIES = {
    "🚗 ДТП": ["дтп", "авария", "столкнов", "машин", "автомоб", "перевернул"],
    "🔥 Пожар": ["пожар", "горел", "огонь", "возгорание", "дым"],
    "☠️ Криминал": ["убил", "убийство", "зарезал", "труп", "застрел", "напал", "избил"],
    "💥 Взрыв": ["взрыв", "детонация", "бомба", "хлопок"],
    "🛩 БПЛА": ["дрон", "бпла", "беспилотник", "пво"],
    "🌊 Катастрофа": ["обрушение", "затопление", "ураган", "землетрясение"],
    "🚨 ЧП": ["происшествие", "нападение", "теракт", "стрельба"]
}

CITIES = {
    "Москва": ["москв", "московск"],
    "Санкт-Петербург": ["питер", "санкт-петерб", "спб"],
    "Самара": ["самар"],
    "Волгоград": ["волгогра"],
    "Екатеринбург": ["екатеринбург", "екб"],
    "Казань": ["казан"],
    "Ставрополь": ["ставрополь", "минводы", "пятигорск", "кисловодск"]
}


def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    sent_links.add(line)
    except:
        pass


def save_memory(link):
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def detect_category(text):
    text = text.lower()
    for cat, words in CATEGORIES.items():
        for w in words:
            if w in text:
                return cat
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
        category_stats[category] = category_stats.get(category, 0) + 1
    if city:
        city_stats[city] = city_stats.get(city, 0) + 1


def clean_title(title):
    title = title.lower()
    bad_words = [
        "в россии", "в москве", "сегодня", "произошло",
        "случилось", "появилось", "сообщается", "стало известно",
        "опубликовано", "видео", "фото", "последствия",
        "подробности", "очевидцы", "экстренные службы", "на месте",
        ":", ",", ".", "!"
    ]
    for w in bad_words:
        title = title.replace(w, "")
    return " ".join(title.split())


def make_news_hash(title):
    words = [w for w in clean_title(title).split() if len(w) > 3]
    return " ".join(list(dict.fromkeys(words))[:7])


def is_similar(title):
    words1 = set(clean_title(title).split())
    for old in sent_titles:
        words2 = set(clean_title(old).split())
        if len(words1.intersection(words2)) >= 3:
            return True
        if SequenceMatcher(None, title, old).ratio() >= 0.82:
            return True
    return False


def get_image_from_article(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for tag, attr, val in [("meta", "property", "og:image"), ("meta", "name", "twitter:image")]:
            meta = soup.find(tag, attrs={attr: val})
            if meta and meta.get("content"):
                return meta["content"]
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src or "logo" in src or "icon" in src:
                continue
            if src.startswith("//"): src = "https:" + src
            elif src.startswith("/"): src = url.split("/")[0] + "//" + url.split("/")[2] + src
            return src
    except Exception as e:
        print("Ошибка фото:", e)
    return None


def ai_rewrite(title, category):
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
        title = title.replace(old, new)
    if any(w in title.lower() for w in ["погиб","теракт","взрыв","стрельба","убийство","дрон","бпла"]):
        title = "⚡ " + title
    return title.strip()


def make_hashtags(category, title):
    tags = ["#Новости"]
    if "🚗" in category: tags.append("#ДТП")
    if "🔥" in category: tags.append("#Пожар")
    if "☠️" in category: tags.append("#Криминал")
    if "💥" in category: tags.append("#Взрыв")
    return " ".join(tags)


def create_post(category, title, link, city=None):
    hashtags = make_hashtags(category, title)
    city_tag = f" #{city}" if city else ""
    return f"""{category}

📰 <b>{title}</b>

🔗 <a href="{link}">Источник</a>

{hashtags}{city_tag}
"""


def send_post(photo, text):
    try:
        if photo:
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            data = {"chat_id": CHANNEL_ID, "photo": photo, "caption": text, "parse_mode": "HTML"}
        else:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
        r = requests.post(url, data=data, timeout=30)
        print(r.text)
    except Exception as e:
        print("Ошибка отправки:", e)


def get_news():
    news = []
    local_hashes = set()
    local_links = set()

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                link = entry.link.strip()
                title = entry.title.strip()
                if not link or link in sent_links or link in local_links:
                    continue
                full_text = f"{title} {link}"
                if not any(w in full_text.lower() for w in HOT_WORDS): continue
                if any(w in full_text.lower() for w in BAD_WORDS): continue
                category = detect_category(full_text)
                if not category: continue
                news_hash = make_news_hash(title)
                if is_similar(title) or news_hash in recent_hashes or news_hash in local_hashes: continue

                original_title = title
                title = ai_rewrite(title, category)
                photo = get_image_from_article(link)
                city = detect_city(original_title)
                update_stats(category, city)
                post = create_post(category, title, link, city)

                sent_links.add(link)
                local_links.add(link)
                sent_titles.append(original_title)
                recent_hashes.add(news_hash)
                local_hashes.add(news_hash)
                save_memory(link)

                # защита памяти
                if len(recent_hashes) > 1000: recent_hashes.clear()
                if len(sent_titles) > 2000: sent_titles.clear()

                news.append((photo, post))

        except Exception as e:
            print("Ошибка RSS:", e)

    return news


def create_digest(news_list, max_items=10):
    if not news_list: return None
    digest_text = "📰 <b>Главное за последний час:</b>\n\n"
    for _, post in news_list[:max_items]:
        first_line = post.strip().split("\n")[2]
        digest_text += f"• {first_line}\n"
    digest_text += "\n#Сводка #Новости #Россия"
    return digest_text


async def main():
    load_memory()
    print("🚨 ЧП бот запущен")

    while True:
        try:
            news = get_news()
            if not news:
                print("📰 Новых новостей нет")
                await asyncio.sleep(120)
                continue

            print(f"📰 Найдено новостей: {len(news)}")
            posted_posts = set()

            # публикуем новости
            for photo, post in news:
                if post in posted_posts:
                    continue
                posted_posts.add(post)
                send_post(photo, post)
                print("✅ Новость опубликована")
                await asyncio.sleep(MIN_POST_INTERVAL)

            # сводка один раз
            digest = create_digest(news, max_items=10)
            if digest:
                send_post(None, digest)
                print("📝 Опубликована сводка")

        except Exception as e:
            print("Общая ошибка:", e)
            await asyncio.sleep(30)


asyncio.run(main())