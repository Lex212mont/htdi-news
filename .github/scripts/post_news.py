#!/usr/bin/env python3
"""Daily НТДИ news digest → @BELTIME_NEWS"""
import os, time, datetime, requests, feedparser, re
from html import escape

TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = "-1003929211757"

SOURCES = [
    # BY
    {"url": "https://www.belta.by/rss/", "name": "БЕЛТА", "region": "by"},
    {"url": "https://www.park.by/rss.xml", "name": "ПВТ", "region": "by"},
    {"url": "https://mpt.gov.by/rss.xml", "name": "Минцифры", "region": "by"},
    # RU
    {"url": "https://tass.ru/rss/v2.xml", "name": "ТАСС", "region": "ru"},
    {"url": "https://ria.ru/export/rss2/archive/index.xml", "name": "РИА", "region": "ru"},
    {"url": "https://rbc.ru/arc/rssfeeds/v1/main/full", "name": "РБК", "region": "ru"},
    {"url": "https://www.kommersant.ru/RSS/news.xml", "name": "Коммерсантъ", "region": "ru"},
    {"url": "https://cnews.ru/inc/rss/news.xml", "name": "CNews", "region": "ru"},
    # Spec
    {"url": "https://habr.com/ru/rss/news/", "name": "Habr", "region": "spec"},
    {"url": "http://feeds.reuters.com/reuters/technologyNews", "name": "Reuters Tech", "region": "spec"},
    {"url": "https://dcunion.ru/feed/", "name": "DC Union", "region": "spec"},
    {"url": "https://www.anti-malware.ru/rss.xml", "name": "Anti-Malware", "region": "spec"},
    {"url": "https://www.infowatch.ru/rss", "name": "InfoWatch", "region": "spec"},
]

REGION_SCORE = {"by": 60, "ru": 50, "spec": 35}
BY_RE = re.compile(r'беларус|белорус|минск|пвт|htp|htdi|нтди|belarus|minsk', re.I)
RU_RE = re.compile(r'россия|российск|москва|russoft|апкит|арпп|russia|russian', re.I)
AI_RE = re.compile(r'\bai\b|искусственн|нейросет|llm|gpt|машинн|ml\b', re.I)
CY_RE = re.compile(r'кибер|хакер|уязвим|вирус|утечк|взлом|security|cyber', re.I)

def score(item, region):
    s = REGION_SCORE.get(region, 0)
    t = (item.get("title","") + " " + item.get("summary",""))
    if BY_RE.search(t): s += 30
    if RU_RE.search(t): s += 20
    if AI_RE.search(t): s += 25
    if CY_RE.search(t): s += 20
    # recency bonus
    published = item.get("published_parsed")
    if published:
        age_h = (time.time() - time.mktime(published)) / 3600
        if age_h < 6:   s += 30
        elif age_h < 12: s += 15
        elif age_h < 24: s += 5
    return s

def fetch_all():
    items = []
    for src in SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for e in feed.entries[:5]:
                items.append({
                    "title":  e.get("title","").strip(),
                    "link":   e.get("link",""),
                    "source": src["name"],
                    "region": src["region"],
                    "published_parsed": e.get("published_parsed"),
                    "summary": e.get("summary",""),
                    "score": 0,
                })
        except Exception as ex:
            print(f"SKIP {src['name']}: {ex}")
    for it in items:
        it["score"] = score(it, it["region"])
    items.sort(key=lambda x: -x["score"])
    return items

FLAG = {"by":"🇧🇾","ru":"🇷🇺","spec":"🔬"}

def build_messages(items):
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    header = f'🗞 <b>Утренний IT-обзор НТДИ | {today}</b>\n\n'
    top7 = items[:7]
    lines = []
    for i, it in enumerate(top7, 1):
        flag = FLAG.get(it["region"],"")
        title = escape(it["title"])
        link  = it["link"]
        name  = escape(it["source"])
        lines.append(
            f'<b>{i}. <a href="{link}">{title}</a></b> {flag}\n'
            f'📌 {name}'
        )
    body = "\n\n".join(lines)
    full = header + body
    # split at ~3800 chars
    if len(full) <= 4096:
        return [full]
    mid = len(top7) // 2
    p1 = header + "\n\n".join(lines[:mid])
    p2 = "\n\n".join(lines[mid:])
    return [p1, p2]

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=20,
    )
    r.raise_for_status()
    print("Sent OK, msg_id:", r.json()["result"]["message_id"])

if __name__ == "__main__":
    items = fetch_all()
    print(f"Fetched {len(items)} items, top score: {items[0]['score'] if items else 0}")
    for msg in build_messages(items):
        send(msg)
        time.sleep(1)
