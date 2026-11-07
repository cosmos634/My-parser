"""Explainable, dependency-free lead scoring."""

import re
from datetime import datetime, timezone

SERVICE_TERMS = {
    "telegram_bot": ["telegram bot", "telegram бот", "телеграм бот", "бот для telegram", "бот для телеграм", "бота для"],
    "website": ["website", "landing", "лендинг", "сайт", "веб-сайт", "интернет-магазин"],
    "automation": ["automation", "автоматизация", "автоматизировать", "автоматизировать бизнес"],
    "python": ["python", "скрипт", "парсер", "парсинг", "автоматический сбор"],
}
BUYER_TERMS = [
    "нужен", "нужна", "нужно", "ищу разработчика", "ищем разработчика",
    "заказать", "закажу", "требуется", "требуются", "ищем исполнителя",
    "нужен программист", "looking for a developer", "need a developer",
    "need a website", "need a bot", "looking for freelancer",
]
SELLER_TERMS = [
    "ищу работу", "предлагаю услуги", "я разработчик", "я программист",
    "возьму заказ", "готов выполнить", "ищу заказ", "my portfolio",
]
BUDGET_RE = re.compile(r"(\d[\d\s,.]*)\s*(₽|руб|рублей|сомони|сом|\$|usd|eur)", re.I)


def detect_language(text: str) -> str:
    if re.search(r"[А-Яа-яЁё]", text):
        return "ru"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def classify(text: str) -> tuple[str, str]:
    value = text.lower()
    category = "other"
    for name, terms in SERVICE_TERMS.items():
        if any(term in value for term in terms):
            category = name
            break
    buyer = any(term in value for term in BUYER_TERMS)
    seller = any(term in value for term in SELLER_TERMS)
    if buyer and not seller and category != "other":
        intent = "buyer_request"
    elif buyer and not seller:
        intent = "developer_search"
    elif seller:
        intent = "freelancer_offer"
    else:
        intent = "unclear"
    return category, intent


def score_lead(title: str, description: str, budget: str | None = None,
               contact: str | None = None, published_at: str | None = None) -> dict:
    text = f"{title}\n{description}".strip()
    category, intent = classify(text)
    points = {}
    points["buyer_intent"] = 30 if intent == "buyer_request" else 20 if intent == "developer_search" else 0
    points["service_match"] = 25 if category != "other" else 0
    points["budget"] = 10 if budget or BUDGET_RE.search(text) else 0
    points["public_contact"] = 10 if contact else 0

    recency = 0
    if published_at:
        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_days = max(0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400)
            recency = 15 if age_days <= 1 else 10 if age_days <= 7 else 5 if age_days <= 30 else 0
        except ValueError:
            recency = 0
    points["recency"] = recency
    points["specificity"] = 10 if len(description.strip()) >= 80 else 5 if description.strip() else 0

    total = max(0, min(100, sum(points.values())))
    if intent in {"freelancer_offer", "unclear"}:
        total = min(total, 49)
    status = "HOT" if total >= 80 else "WARM" if total >= 50 else "LOW"
    return {
        "category": category,
        "intent": intent,
        "language": detect_language(text),
        "score": total,
        "status": status,
        "score_breakdown": points,
    }
