import json, re, html, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
 ("गोरखापत्र दैनिक","https://gorkhapatraonline.com/rss"),
 ("कान्तिपुर दैनिक","https://news.google.com/rss/search?q=site%3Aekantipur.com&hl=ne&gl=NP&ceid=NP%3Ane"),
 ("OnlineKhabar","https://www.onlinekhabar.com/feed"),
 ("The Kathmandu Post","https://kathmandupost.com/rss"),
 ("Ratopati","https://www.ratopati.com/feed"),
 ("Setopati","https://www.setopati.com/feed"),
 ("Ujyaalo Online","https://ujyaaloonline.com/rss"),
 ("NepalNews","https://nepalnews.com/feed"),
 ("Himal Press","https://himalpress.com/feed/"),
 ("Khabarhub","https://khabarhub.com/feed/"),
 ("Lokaantar","https://www.lokaantar.com/feed/"),
 ("Nepal Samaya","https://nepalsamaya.com/feed"),
 ("Thaha Khabar","https://thahakhabar.com/rss/"),
 ("Himalkhabar","https://www.himalkhabar.com/feed"),
 ("Techpana","https://www.techpana.com/feed"),
]
def local_text(node, names):
    for child in list(node):
        tag = child.tag.rsplit("}",1)[-1].lower()
        if tag in names:
            return "".join(child.itertext()).strip()
    return ""
def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", value).strip()
def parse_date(value):
    if not value: return ""
    try: return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception:
        try: return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc).isoformat()
        except Exception: return ""

items, failed = [], []
for source, url in FEEDS:
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; TrilochanNewsBot/1.0)", "Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml"})
        with urllib.request.urlopen(req, timeout=25) as response:
            root = ET.fromstring(response.read())
        entries = [n for n in root.iter() if n.tag.rsplit("}",1)[-1].lower() in ("item","entry")]
        if not entries: raise ValueError("RSS/Atom entries not found")
        count = 0
        for entry in entries[:40]:
            title = clean(local_text(entry, {"title"}))
            link = ""
            for child in list(entry):
                if child.tag.rsplit("}",1)[-1].lower() == "link":
                    link = (child.attrib.get("href") or child.text or "").strip()
                    if link: break
            summary = clean(local_text(entry, {"description","summary","encoded","content"}))
            published = parse_date(local_text(entry, {"pubdate","published","updated","date"}))
            if title and link.startswith("http"):
                items.append({"source":source,"title":title,"url":link,"summary":summary[:480],"published":published})
                count += 1
        if count == 0: raise ValueError("No usable headline/link entries")
    except Exception as exc:
        failed.append({"source":source,"error":str(exc)[:160]})

seen, unique = set(), []
for item in sorted(items, key=lambda x:x["published"], reverse=True):
    key = item["url"].split("#",1)[0].rstrip("/")
    if key not in seen:
        seen.add(key)
        unique.append(item)
payload = {
    "updated":datetime.now(timezone.utc).isoformat(),
    "count":len(unique),
    "sources_total":len(FEEDS),
    "sources_ok":len(FEEDS)-len(failed),
    "failed_sources":failed,
    "items":unique[:220]
}
with open("current-affairs/news.json","w",encoding="utf-8") as file:
    json.dump(payload,file,ensure_ascii=False,indent=2)
print(f"Saved {len(payload['items'])} unique headlines from {payload['sources_ok']}/{payload['sources_total']} feeds.")
if not payload["items"]:
    raise SystemExit("No news feeds returned usable headlines; refusing to publish an empty feed.")


# Build a growing Loksewa MCQ bank from verified RSS metadata.
# These questions test facts explicitly present in the feed: publication date and publisher.
# No article facts are guessed or generated from ambiguous summaries.
import hashlib, random
from datetime import date, timedelta
from pathlib import Path

QUESTION_FILE = Path("current-affairs/questions.json")
try:
    old_bank = json.loads(QUESTION_FILE.read_text(encoding="utf-8"))
except Exception:
    old_bank = {"questions": []}

all_questions = old_bank.get("questions", [])
known_ids = {q.get("id") for q in all_questions if q.get("id")}
publishers = sorted({x.get("source", "").strip() for x in unique if x.get("source")})
published_dates = sorted({
    x.get("published", "")[:10]
    for x in unique
    if re.match(r"^\\d{4}-\\d{2}-\\d{2}", x.get("published", ""))
})

def nepali_digits(value):
    return str(value).translate(str.maketrans("0123456789", "०१२३४५६७८९"))

def date_label(iso_date):
    try:
        d = date.fromisoformat(iso_date)
        return "ई.सं. " + nepali_digits(d.strftime("%Y-%m-%d"))
    except Exception:
        return iso_date

def stable_shuffle(values, seed):
    values = list(dict.fromkeys(values))
    random.Random(seed).shuffle(values)
    return values

for item in unique:
    title = clean(item.get("title", ""))[:180]
    source = clean(item.get("source", ""))
    url = item.get("url", "")
    published = item.get("published", "")[:10]
    if not title or not source or not url.startswith("http"):
        continue
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:18]

    # MCQ 1: exact publication date from RSS metadata.
    if re.match(r"^\\d{4}-\\d{2}-\\d{2}$", published):
        try:
            correct_date = date.fromisoformat(published)
            distractor_dates = [
                (correct_date + timedelta(days=delta)).isoformat()
                for delta in (-2, -1, 1)
            ]
            date_options = [date_label(d) for d in stable_shuffle(
                [published] + distractor_dates, key + "-date"
            )]
            correct_label = date_label(published)
            qid = "news-date-" + key
            if qid not in known_ids:
                all_questions.append({
                    "id": qid,
                    "topic": "समाचारको मिति",
                    "level": "समसामयिक",
                    "question": "तलको समाचार कहिले प्रकाशित भएको थियो? — " + title,
                    "options": date_options,
                    "answer": date_options.index(correct_label),
                    "explanation": "RSS मा उपलब्ध प्रकाशन मिति " + correct_label + " हो।",
                    "source": url,
                    "news_source": source,
                    "news_date": published
                })
                known_ids.add(qid)
        except Exception:
            pass

    # MCQ 2: publisher/source attribution from the feed metadata.
    if len(publishers) >= 4:
        wrong_sources = [s for s in publishers if s != source]
        seed_sources = stable_shuffle(wrong_sources, key + "-source")[:3]
        source_options = stable_shuffle([source] + seed_sources, key + "-choices")
        qid = "news-source-" + key
        if qid not in known_ids:
            all_questions.append({
                "id": qid,
                "topic": "समाचार स्रोत",
                "level": "समसामयिक",
                "question": "यो समाचार कुन सञ्चारमाध्यममा प्रकाशित भएको हो? — " + title,
                "options": source_options,
                "answer": source_options.index(source),
                "explanation": "यो समाचारको स्रोत " + source + " हो।",
                "source": url,
                "news_source": source,
                "news_date": published
            })
            known_ids.add(qid)

# Keep the full growing bank; stable IDs prevent duplicates across 30-minute runs.
# Curated questions remain untouched and appear alongside generated questions.
bank = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "total": len(all_questions),
    "generated_from_news": sum(1 for q in all_questions if str(q.get("id", "")).startswith("news-")),
    "questions": all_questions
}
QUESTION_FILE.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Loksewa MCQ bank: {len(all_questions)} total questions, "
      f"{bank['generated_from_news']} generated from news metadata.")
