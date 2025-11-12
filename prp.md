# PRP — Trial “Hybrid Scraper v0.1” (Moneycontrol Markets Listing)

## 1) Tujuan

Membuat **skrip sederhana** yang:

* Mengambil **1 halaman listing** (tanpa mengikuti link detail).
* Mengekstrak **kartu berita** (judul, url, ringkas, waktu/label).
* Menggunakan **LLM (via LiteLLM)** untuk **menormalisasi** hasil ke skema JSON konsisten + memberi **confidence**.
* Menyimpan output ke **JSONL** lokal.

> Fokus: *proof-of-concept* pipeline **hybrid** (pattern → kandidat → LLM → validasi ringan). Bukan scraping masif.

## 2) Ruang Lingkup (Scope)

* **Input**: 1 URL listing (page-1).

* **Output**: `outputs/moneycontrol_listing_page1.jsonl`

* **Field target (per item)**:

  * `headline` *(string, wajib)*
  * `url` *(string, absolut, wajib)*
  * `summary` *(string, optional)*
  * `published_label` *(string, optional, mis. “x hours ago” / “Today”)*
  * `category` = `"markets"` *(konstan untuk trial)*
  * `confidence` *(0–1, dari LLM)*
  * `evidence.snippet` *(potongan teks yang dipakai)*

* **Tidak termasuk (out-of-scope)**:

  * Crawl ke halaman detail berita
  * Multi-page, depth > 0
  * Penanganan CAPTCHA/anti-bot khusus

## 3) Legal & Etika (Wajib)

* **Hormati robots.txt/ToS** dan batasi ke 1 halaman untuk trial.
* **Politeness**: User-Agent custom, 1 request/page, delay kecil bila perlu.
* Simpan raw HTML hanya untuk *debug* lokal.

## 4) Arsitektur Minimal

```
trial_hybrid/
  core/
    fetcher.py         # httpx + headers, timeout
    parser.py          # extract kartu listing → kandidat fields
    normalizer.py      # perapihan url absolut, trim text
    llm.py             # wrapper LiteLLM (JSON-mode)
    validate.py        # validasi simple (url, panjang teks)
  run_trial.py         # main runner
  schemas.py           # Pydantic model NewsItem
  prompts.py           # prompt LLM anti-halusinasi
  outputs/             # JSONL hasil
  fixtures/            # (opsional) simpan 1 sample HTML untuk test offline
```

## 5) Alur Proses

1. **Fetch** halaman listing (GET sekali).
2. **Parse pattern**: cari *cards* berita (heuristic: tag dengan anchor + heading + snippet).
3. **Bangun kandidat** per item: `{headline?, url?, summary?, published_label?}`
4. **LLM normalize** (LiteLLM): kirim **kandidat ringkas (snippet pendek)** → minta **JSON** final sesuai skema + `confidence` + `evidence`.
5. **Validasi ringan**: `url` absolut, `headline` non-kosong, panjang wajar.
6. **Simpan** setiap item ke JSONL.

## 6) Skema Data (Pydantic)

```python
class NewsItem(BaseModel):
    source: Literal["moneycontrol"]
    category: Literal["markets"]
    headline: str
    url: HttpUrl
    summary: str | None = None
    published_label: str | None = None
    confidence: float = Field(ge=0, le=1)
    evidence: dict | None = None
```

## 7) Prompt LLM (LiteLLM) — *JSON only, anti-halusinasi*

**Instruksi inti**:

* “Kembalikan **JSON valid** sesuai skema `NewsItem` (tanpa teks lain).”
* “Gunakan **HANYA** teks kandidat yang diberikan. Jika field tidak jelas, set `null`.”
* “`confidence` 0.0–1.0; 0.9 jika bukti sangat jelas; 0.6 jika dugaan.”
* “`summary` ≤ 200 karakter, ringkas; jangan tambahkan fakta baru.”

**Konteks yang dikirim** (per item):

* `page_context`: “moneycontrol › business › markets (listing)”
* `candidate`: `headline?`, `url?`, `snippet?`, `published_label?`
* `schema`: contoh JSON target (tanpa data sensitif)

## 8) Konfigurasi LiteLLM

**Env vars**:

```
LITELLM_API_BASE=https://<proxy-anda>         # contoh: https://proxy.ximplify.id
LITELLM_API_KEY=sk-xxxx
LITELLM_MODEL=openai/gpt-4o-mini              # contoh; ganti sesuai ketersediaan
```

**Catatan**: pilih model *economical* + dukungan JSON output.

## 9) Heuristik Parsing (pattern sisi listing)

* Seleksi **kartu**: cari elemen yang mengandung:

  * anchor `<a>` (link berita) + teks judul (heading/h2/h3 atau class “title”)
  * deskripsi/lede pendek (p/span) → `summary`
  * label waktu (mis. “X hours ago”, “Today”, tanggal)
* Normalisasi **url absolut** via `urllib.parse.urljoin`.
* **Top-N**: ambil maksimal 20 item pertama (trial).

## 10) Validasi Ringkas

* `headline` panjang 5–240 karakter.
* `url` skema `http/https` dan host `moneycontrol.com`.
* Potong `summary` > 300 chars.
* Jika tidak lolos, tandai item (skip atau `confidence=0.0`).

## 11) Output

* File: `outputs/moneycontrol_listing_page1.jsonl`
* Format: **1 baris per berita** (JSON), mudah di-pipe ke downstream/RAG.

## 12) Evaluasi Keberhasilan (Acceptance Criteria)

* Minimal **10 item** tervalidasi dari halaman listing.
* JSONL valid (tanpa baris rusak), semua `url` absolut.
* **Tidak ada** error LLM (parse JSON) pada ≥95% item.
* Rata-rata `confidence` ≥0.7 untuk item dengan kandidat lengkap.

## 13) Risiko & Mitigasi

* **Layout berubah** → Gunakan selector heuristik (beberapa fallback).
* **Anti-bot** → Batasi 1 halaman, set UA headers; siap gunakan fixture offline.
* **Biaya LLM** → Kirim **snippet pendek** (≤ 500–800 char/item).
* **Halusinasi** → Prompt ketat + validasi + evidence snippet.

## 14) Rencana Uji (Test Plan)

* **Smoke**: jalankan sekali, cek 10–20 item, manual spot check.
* **Offline**: simpan HTML ke `fixtures/` → jalankan parser tanpa network (deterministik).
* **JSON schema**: validasi Pydantic saat write.

---

## Lampiran: Skeleton Kode Minimal

```python
# run_trial.py
import os, json, asyncio
from core.fetcher import fetch_html
from core.parser import extract_listing_candidates
from core.normalizer import normalize_item
from core.llm import normalize_with_llm
from core.validate import is_valid_news
from pathlib import Path

URL = "https://www.moneycontrol.com/news/business/markets/page-1/"
OUT = Path("outputs/moneycontrol_listing_page1.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)

async def main():
    html = await fetch_html(URL)
    candidates = extract_listing_candidates(html, base_url=URL)

    with OUT.open("w", encoding="utf-8") as f:
        for cand in candidates[:20]:
            cand = normalize_item(cand, base_url=URL)  # urljoin, trim
            record = await normalize_with_llm(cand)    # LiteLLM call → JSON dict
            if is_valid_news(record):
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    asyncio.run(main())
```

```python
# core/fetcher.py
import httpx

HEADERS = {
    "User-Agent": "HybridScraperTrial/0.1 (+https://example.org)"
}

async def fetch_html(url: str, timeout=15):
    async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text
```

```python
# core/parser.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_listing_candidates(html: str, base_url: str):
    soup = BeautifulSoup(html, "lxml")
    items = []

    # Heuristik: cari blok yang punya <a> judul + snippet
    for card in soup.select("a"):
        headline = card.get_text(strip=True)
        href = card.get("href")
        if not headline or not href:
            continue

        # Coba cari sibling/parent snippet & time label
        parent = card.find_parent()
        snippet = None
        time_label = None
        if parent:
            # contoh pendek—akan ditingkatkan saat implementasi
            p = parent.find("p")
            if p: snippet = p.get_text(" ", strip=True)
            small = parent.find(["span","time","em","small"])
            if small: time_label = small.get_text(" ", strip=True)

        items.append({
            "headline": headline,
            "url": urljoin(base_url, href),
            "summary": snippet,
            "published_label": time_label,
            "source": "moneycontrol",
            "category": "markets",
        })
    return items
```

```python
# core/llm.py
import os, json
from litellm import acompletion

MODEL = os.getenv("LITELLM_MODEL", "openai/gpt-4o-mini")
API_BASE = os.getenv("LITELLM_API_BASE")
API_KEY  = os.getenv("LITELLM_API_KEY")

SYSTEM = """You are a strict JSON normalizer.
Return ONLY valid JSON for NewsItem; never add fields.
If unsure, set fields to null. confidence in [0,1]."""

def build_user_prompt(cand: dict) -> str:
    schema_example = {
      "source":"moneycontrol","category":"markets",
      "headline":"...", "url":"https://...", "summary":"...", 
      "published_label":"...", "confidence":0.0,
      "evidence":{"snippet":"..."}
    }
    return (
      "SCHEMA:\n" + json.dumps(schema_example) + "\n\n"
      "CANDIDATE:\n" + json.dumps({
          "headline": cand.get("headline"),
          "url": cand.get("url"),
          "summary": cand.get("summary"),
          "published_label": cand.get("published_label"),
      }, ensure_ascii=False)
      + "\n\nRules: Use only CANDIDATE text. Provide evidence.snippet from candidate summary or headline."
    )

async def normalize_with_llm(cand: dict) -> dict:
    prompt = build_user_prompt(cand)
    resp = await acompletion(
        model=MODEL,
        api_base=API_BASE,
        api_key=API_KEY,
        messages=[{"role":"system","content":SYSTEM},
                  {"role":"user","content":prompt}],
        temperature=0,
        response_format={"type":"json_object"}  # minta JSON
    )
    txt = resp.choices[0].message.content
    data = json.loads(txt)
    # fallback/merge constant fields if missing
    data.setdefault("source", "moneycontrol")
    data.setdefault("category", "markets")
    # ensure evidence.snippet
    if not data.get("evidence"):
        data["evidence"] = {"snippet": (cand.get("summary") or cand.get("headline") or "")[:240]}
    return data
```

```python
# core/validate.py
from urllib.parse import urlparse

def is_valid_news(d: dict) -> bool:
    try:
        h = (d.get("headline") or "").strip()
        u = (d.get("url") or "").strip()
        if len(h) < 5: return False
        netloc = urlparse(u).netloc
        if "moneycontrol.com" not in netloc: return False
        return True
    except Exception:
        return False
```

---

## 15) Langkah Implementasi (To-Do)

* [ ] Siapkan venv & dependency: `httpx`, `beautifulsoup4`, `lxml`, `pydantic`, `litellm`, `python-dotenv` (opsional).
* [ ] Isi `LITELLM_API_BASE`, `LITELLM_API_KEY`, `LITELLM_MODEL`.
* [ ] Jalankan `python run_trial.py`.
* [ ] Periksa `outputs/*.jsonl` dan spot-check 5 item.

---

Kalau cocok, next step:

* Tambah **detektor kartu** yang lebih presisi (selector berlapis).
* Tambah **pengaya waktu** (parsing tanggal relatif kalau ada).
* Bandingkan **pattern-only vs pattern+LLM** (ukur akurasi/kelengkapan).
* Siapkan **fixture HTML** supaya parser tetap jalan tanpa network.
