import json, re, urllib.request, xml.etree.ElementTree as ET
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
]
def clean(s):
 return re.sub(r"\\s+"," ",re.sub(r"<[^>]+>"," ",s or "")).strip()
items=[]; failed=[]
for source,url in FEEDS:
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; TrilochanNewsBot/1.0)"})
  data=urllib.request.urlopen(req,timeout=20).read()
  root=ET.fromstring(data)
  entries=root.findall(".//item")
  if not entries:
   ns={"a":"http://www.w3.org/2005/Atom"}
   entries=root.findall(".//a:entry",ns)
  for e in entries[:35]:
   def val(tag):
    x=e.find(tag)
    return x.text if x is not None and x.text else ""
   title=clean(val("title"))
   link=val("link")
   if not link:
    x=e.find("{http://www.w3.org/2005/Atom}link")
    link=x.attrib.get("href","") if x is not None else ""
   desc=clean(val("description") or val("summary") or val("{http://www.w3.org/2005/Atom}summary"))
   pub=val("pubDate") or val("published") or val("updated")
   try: dt=parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
   except: 
    try: dt=datetime.fromisoformat(pub.replace("Z","+00:00")).astimezone(timezone.utc).isoformat()
    except: dt=""
   if title and link.startswith("http"):
    items.append({"source":source,"title":title,"url":link,"summary":desc[:420],"published":dt})
 except Exception as ex:
  failed.append({"source":source,"error":str(ex)[:180]})
seen=set(); unique=[]
for x in sorted(items,key=lambda z:z["published"],reverse=True):
 key=x["url"]
 if key not in seen: seen.add(key); unique.append(x)
payload={"updated":datetime.now(timezone.utc).isoformat(),"count":len(unique),"sources":len(FEEDS),"failed_sources":failed,"items":unique[:160]}
with open("current-affairs/news.json","w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,indent=2)
print(f"Saved {len(payload['items'])} headlines; failed feeds: {len(failed)}")
