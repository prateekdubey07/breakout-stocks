import os
import requests
from datetime import datetime, timedelta


NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "")


def _sentiment(headline: str) -> str:
    bull = ["surge", "beat", "record", "upgrade", "buy", "breakout", "growth", "strong"]
    bear = ["miss", "cut", "downgrade", "sell", "decline", "loss", "weak", "recall"]
    h = headline.lower()
    if any(w in h for w in bull):
        return "bullish"
    if any(w in h for w in bear):
        return "bearish"
    return "neutral"


def fetch_news(tickers: list[str]) -> list[dict]:
    results = []
    seen: set[str] = set()
    since = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    for ticker in tickers[:5]:
        if NEWSAPI_KEY:
            try:
                r = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": ticker, "sortBy": "publishedAt", "pageSize": 5,
                            "from": since, "apiKey": NEWSAPI_KEY},
                    timeout=5,
                )
                for art in r.json().get("articles", []):
                    h = art.get("title", "")
                    if h and h not in seen:
                        seen.add(h)
                        results.append({
                            "ticker": ticker, "headline": h,
                            "source": art.get("source", {}).get("name", "NewsAPI"),
                            "url": art.get("url", ""),
                            "sentiment": _sentiment(h),
                            "published_at": art.get("publishedAt", ""),
                        })
            except Exception:
                pass

        if FINNHUB_KEY:
            try:
                r = requests.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={"symbol": ticker, "from": since, "to": today,
                            "token": FINNHUB_KEY},
                    timeout=5,
                )
                for art in r.json()[:5]:
                    h = art.get("headline", "")
                    if h and h not in seen:
                        seen.add(h)
                        results.append({
                            "ticker": ticker, "headline": h,
                            "source": art.get("source", "Finnhub"),
                            "url": art.get("url", ""),
                            "sentiment": _sentiment(h),
                            "published_at": str(art.get("datetime", "")),
                        })
            except Exception:
                pass

    return results
