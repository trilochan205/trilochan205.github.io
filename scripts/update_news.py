import json, re, html, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
 ("गोरखापत्र दैनिक","https://gorkhapatraonline.com/rss"),
 ("कान्तिपुर दैनिक","https://ekantipur.com/rss"),
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
    return re.sub(r"\\s+", " ", value).strip()
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
