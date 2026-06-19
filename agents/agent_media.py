import httpx
from xml.etree import ElementTree
from utils.logger import logger

NEGATIVE_KEYWORDS = [
    "мошенничество", "обман", "кража", "хищение", "долг", "банкрот",
    "ликвидация", "арест", "уголовное дело", "налоговая схема",
    "обнал", "незаконный",
]


async def fetch(company_name: str, inn: str = "") -> dict:
    articles = []
    query = f"{company_name} {inn}".strip()
    errors = []

    # Source 1: Яндекс.Новости RSS
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.get("https://news.yandex.ru/search.rss", params={"text": query}, follow_redirects=True)
            if resp.status_code == 200 and resp.content:
                root = ElementTree.fromstring(resp.content)
                for item in root.iter("item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub_date = item.findtext("pubDate", "")
                    sentiment = "negative" if any(kw in title.lower() for kw in NEGATIVE_KEYWORDS) else "neutral"
                    articles.append({"title": title, "date": pub_date, "url": link, "sentiment": sentiment, "source": "Яндекс.Новости"})
    except Exception as e:
        errors.append(f"Яндекс.Новости: {e}")

    # Source 2: Google News RSS
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            resp = await client.get("https://news.google.com/rss/search", params={"q": query, "hl": "ru", "gl": "RU"}, follow_redirects=True)
            if resp.status_code == 200 and resp.content:
                root = ElementTree.fromstring(resp.content)
                for item in root.iter("item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub_date = item.findtext("pubDate", "")
                    sentiment = "negative" if any(kw in title.lower() for kw in NEGATIVE_KEYWORDS) else "neutral"
                    articles.append({"title": title, "date": pub_date, "url": link, "sentiment": sentiment, "source": "Google News"})
    except Exception as e:
        errors.append(f"Google News: {e}")

    negative_articles = [a for a in articles if a["sentiment"] == "negative"]
    fraud_mentions = any("мошенничеств" in a["title"].lower() or "обман" in a["title"].lower() for a in articles)

    result = {
        "source": "СМИ/Яндекс.Новости/Google News",
        "negative_media": len(negative_articles) > 0,
        "fraud_mentions": fraud_mentions,
        "media_articles": articles,
        "website_active": False,
        "website_url": "",
        "social_networks": [],
        "overall_sentiment": "negative" if len(negative_articles) > len(articles) / 2 else "unknown",
        "error": None,
        "total_articles": len(articles),
    }

    if errors:
        result["note"] = "; ".join(errors)

    return result
