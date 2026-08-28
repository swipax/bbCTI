"""
Otomatik CTI Bulteni - toplayici script.

Ne yapar:
1. ThreatFox ve URLhaus'tan son IOC'lari ceker
2. Daha once islenmis olanlari (seen_ids.json) eler, sadece yenileri birakir
3. En yuksek confidence'a sahip en fazla MAX_ITEMS_PER_RUN taneyi secer
4. Bu secili grubu TEK bir Grok API cagrisinda (batch) ozetletir
5. Sonucu docs/data/latest.json'a yazar

Gerekli ortam degiskenleri (GitHub Actions Secrets uzerinden gelir):
  ABUSECH_AUTH_KEY  -> https://auth.abuse.ch/ adresinden ucretsiz alinir
  XAI_API_KEY       -> https://console.x.ai adresinden alinir
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

ABUSECH_AUTH_KEY = os.environ["ABUSECH_AUTH_KEY"]
XAI_API_KEY = os.environ["XAI_API_KEY"]

# Gunde en fazla kac yeni IOC'yi AI'a gonderelim (token maliyetini kontrol altinda tutar)
MAX_ITEMS_PER_RUN = 20

DATA_DIR = Path("docs/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEEN_FILE = DATA_DIR / "seen_ids.json"
OUTPUT_FILE = DATA_DIR / "latest.json"


def load_seen_ids():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen_ids(seen):
    # Dosyanin sonsuza kadar buyumesini onlemek icin son 5000 id'yi tut
    SEEN_FILE.write_text(json.dumps(sorted(seen)[-5000:]))


def fetch_threatfox():
    resp = requests.post(
        "https://threatfox-api.abuse.ch/api/v1/",
        headers={"Auth-Key": ABUSECH_AUTH_KEY},
        json={"query": "get_iocs", "days": 1},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("query_status") != "ok":
        return []

    items = []
    for entry in data.get("data", []):
        items.append({
            "source": "threatfox",
            "id": f"threatfox-{entry['id']}",
            "ioc": entry.get("ioc"),
            "ioc_type": entry.get("ioc_type"),
            "malware": entry.get("malware_printable"),
            "confidence": entry.get("confidence_level", 0),
            "first_seen": entry.get("first_seen"),
            "tags": entry.get("tags") or [],
            "reference": entry.get("reference"),
        })
    return items


def fetch_urlhaus():
    resp = requests.get(
        "https://urlhaus-api.abuse.ch/v1/urls/recent/limit/50/",
        headers={"Auth-Key": ABUSECH_AUTH_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("query_status") != "ok":
        return []

    items = []
    for entry in data.get("urls", []):
        items.append({
            "source": "urlhaus",
            "id": f"urlhaus-{entry['id']}",
            "ioc": entry.get("url"),
            "ioc_type": "url",
            "malware": ",".join(entry.get("tags") or []),
            "confidence": 75,  # URLhaus confidence puani vermiyor, sabit deger kullaniyoruz
            "first_seen": entry.get("date_added"),
            "tags": entry.get("tags") or [],
            "reference": entry.get("urlhaus_reference"),
        })
    return items


def summarize_with_grok(items):
    """Tum grubu TEK bir API cagrisinda ozetletir. Item sayisi arttikca cagri
    sayisi degil, tek istegin icerigi buyur -> maliyet neredeyse sabit kalir."""
    if not items:
        return {}

    prompt_items = [
        {
            "id": it["id"],
            "ioc": it["ioc"],
            "ioc_type": it["ioc_type"],
            "malware": it["malware"],
            "tags": it["tags"],
        }
        for it in items
    ]

    system_prompt = (
        "Sen bir tehdit istihbarati analistisin. Sana JSON formatinda bir IOC "
        "listesi verilecek. Her IOC icin: (1) ne oldugunu ve neden onemli "
        "oldugunu aciklayan 1-2 cumlelik Turkce bir ozet, (2) 'low', 'medium' "
        "veya 'high' seviyesinde bir risk derecesi uret. SADECE bir JSON array "
        "dondur, her eleman {id, summary_tr, severity} alanlarina sahip olsun. "
        "Baska hicbir metin, aciklama veya markdown kod bloğu ekleme."
    )

    resp = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "grok-4-fast",  # ucuz/hizli varyant - console.x.ai'dan guncel adini kontrol et
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(prompt_items, ensure_ascii=False)},
            ],
            "temperature": 0.3,
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()

    # Model bazen ```json ... ``` seklinde sarmalayabiliyor, temizleyelim
    if content.startswith("```"):
        content = content.strip("`")
        content = content.replace("json", "", 1).strip()

    results = json.loads(content)
    return {r["id"]: r for r in results}


def main():
    seen = load_seen_ids()

    all_items = fetch_threatfox() + fetch_urlhaus()
    new_items = [it for it in all_items if it["id"] not in seen]
    new_items.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    batch = new_items[:MAX_ITEMS_PER_RUN]

    print(f"Toplam cekilen: {len(all_items)} | yeni: {len(new_items)} | islenecek: {len(batch)}")

    summaries = summarize_with_grok(batch)

    enriched = []
    for it in batch:
        s = summaries.get(it["id"], {})
        it["summary_tr"] = s.get("summary_tr", "")
        it["severity"] = s.get("severity", "unknown")
        enriched.append(it)

    existing = []
    if OUTPUT_FILE.exists():
        existing = json.loads(OUTPUT_FILE.read_text()).get("items", [])

    # Yeni gelenler basa, toplamda en fazla 200 kayit sitede tutulur
    combined = (enriched + existing)[:200]

    OUTPUT_FILE.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": combined,
    }, ensure_ascii=False, indent=2))

    seen.update(it["id"] for it in batch)
    save_seen_ids(seen)

    print(f"{len(batch)} yeni IOC islendi, latest.json guncellendi.")


if __name__ == "__main__":
    main()
