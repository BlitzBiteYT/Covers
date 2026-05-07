"""
Anime Cover Database Scraper
============================
Dual-source synchronization: Jikan (MAL) as primary, AniList as fallback.
Runs incrementally — never deletes existing entries.

Usage:
    pip install requests
    python scraper.py
"""

import json
import os
import time
import unicodedata
import re
import requests

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
DATABASE_FILE = "database.json"
JIKAN_BASE    = "https://api.jikan.moe/v4"
ANILIST_URL   = "https://graphql.anilist.co"

# Seconds to sleep between Jikan calls (their public limit is ~3 req/s).
JIKAN_SLEEP   = 1.5

# AniList allows 90 req/min on public access — 0.67 s/req is safe.
ANILIST_SLEEP = 0.7


# ──────────────────────────────────────────────
# TITLE NORMALISATION  (used for fuzzy matching)
# ──────────────────────────────────────────────
def normalize_title(title: str) -> str:
    """
    Lower-case, strip accents, collapse whitespace, remove punctuation.
    'Sword Art Online: Alicization' → 'sword art online alicization'
    """
    if not title:
        return ""
    # NFKD decomposition strips accent marks
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    # Remove everything that isn't alphanumeric or whitespace
    cleaned = re.sub(r"[^a-z0-9\s]", "", ascii_str.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def titles_match(a: str, b: str) -> bool:
    """Return True when two titles normalise to the same string."""
    return normalize_title(a) == normalize_title(b)


# ──────────────────────────────────────────────
# DATABASE HELPERS
# ──────────────────────────────────────────────
def load_database() -> dict:
    """
    Load the existing database.json.
    Returns a dict keyed by mal_id (str) for fast lookup.
    Falls back to an empty dict if the file is missing / invalid.
    """
    if not os.path.exists(DATABASE_FILE):
        print(f"[DB] '{DATABASE_FILE}' not found — starting fresh.")
        return {}
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Support both list and dict formats written by previous runs
        if isinstance(raw, list):
            return {str(entry["mal_id"]): entry for entry in raw if "mal_id" in entry}
        if isinstance(raw, dict):
            return raw
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"[DB] Warning: could not parse database ({exc}). Starting fresh.")
    return {}


def save_database(db: dict) -> None:
    """Persist the database as a pretty-printed JSON list sorted by title."""
    entries = sorted(db.values(), key=lambda e: e.get("title", "").lower())
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"[DB] Saved {len(entries)} entries → '{DATABASE_FILE}'")


# ──────────────────────────────────────────────
# JIKAN  (MyAnimeList)
# ──────────────────────────────────────────────
def fetch_jikan_season_now() -> list[dict]:
    """
    Retrieve all pages of /seasons/now from Jikan.
    Returns a flat list of raw Jikan anime objects.
    """
    results = []
    page = 1
    while True:
        url = f"{JIKAN_BASE}/seasons/now?page={page}"
        print(f"[Jikan] Fetching page {page} …")
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            print(f"[Jikan] Request error on page {page}: {exc}")
            break

        data = payload.get("data", [])
        if not data:
            break

        results.extend(data)

        # Jikan paginates; check if more pages exist
        pagination = payload.get("pagination", {})
        if not pagination.get("has_next_page", False):
            break

        page += 1
        time.sleep(JIKAN_SLEEP)

    print(f"[Jikan] Fetched {len(results)} seasonal anime.")
    return results


def parse_jikan_entry(raw: dict) -> dict | None:
    """
    Extract the fields we care about from a raw Jikan object.
    Returns None if the entry is malformed.
    """
    mal_id = raw.get("mal_id")
    if not mal_id:
        return None

    title = (
        raw.get("title_english")
        or raw.get("title")
        or raw.get("title_japanese")
        or "Unknown"
    )

    # Prefer the large image; fall back through the chain
    images = raw.get("images", {})
    jpg    = images.get("jpg", {})
    cover  = (
        jpg.get("large_image_url")
        or jpg.get("image_url")
        or images.get("webp", {}).get("large_image_url")
        or images.get("webp", {}).get("image_url")
    )

    return {
        "title":      title,
        "mal_id":     str(mal_id),
        "anilist_id": None,          # filled in later
        "cover_url":  cover or "",
        "source_used": "Jikan" if cover else "pending",
    }


# ──────────────────────────────────────────────
# ANILIST  (GraphQL)
# ──────────────────────────────────────────────
ANILIST_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 10) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      title {
        romaji
        english
        native
      }
      coverImage {
        extraLarge
        large
      }
    }
  }
}
"""

ANILIST_SEASONAL_QUERY = """
query ($season: MediaSeason, $seasonYear: Int, $page: Int) {
  Page(page: $page, perPage: 50) {
    pageInfo {
      hasNextPage
    }
    media(season: $season, seasonYear: $seasonYear, type: ANIME, sort: POPULARITY_DESC) {
      id
      title {
        romaji
        english
        native
      }
      coverImage {
        extraLarge
        large
      }
    }
  }
}
"""


def _anilist_post(query: str, variables: dict) -> dict | None:
    """Raw POST to AniList GraphQL endpoint. Returns parsed JSON or None."""
    try:
        resp = requests.post(
            ANILIST_URL,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"[AniList] Request error: {exc}")
        return None


def search_anilist_by_title(title: str) -> dict | None:
    """
    Search AniList for an anime by title.
    Returns the best-matched media object or None.
    """
    data = _anilist_post(ANILIST_QUERY, {"search": title, "page": 1})
    if not data:
        return None

    media_list = (
        data.get("data", {})
            .get("Page", {})
            .get("media", [])
    )
    if not media_list:
        return None

    # Try to find an exact normalised-title match first
    for media in media_list:
        al_titles = [
            media["title"].get("english") or "",
            media["title"].get("romaji") or "",
            media["title"].get("native") or "",
        ]
        if any(titles_match(title, t) for t in al_titles if t):
            return media

    # Fall back to the top search result
    return media_list[0]


def fetch_anilist_season(season: str, year: int) -> list[dict]:
    """
    Fetch a full seasonal list from AniList (used to find shows
    that Jikan may have missed).

    season: "WINTER" | "SPRING" | "SUMMER" | "FALL"
    year:   e.g. 2025
    """
    results = []
    page = 1
    while True:
        data = _anilist_post(
            ANILIST_SEASONAL_QUERY,
            {"season": season, "seasonYear": year, "page": page},
        )
        time.sleep(ANILIST_SLEEP)

        if not data:
            break

        page_data = data.get("data", {}).get("Page", {})
        media_list = page_data.get("media", [])
        results.extend(media_list)

        if not page_data.get("pageInfo", {}).get("hasNextPage", False):
            break
        page += 1

    print(f"[AniList] Fetched {len(results)} seasonal entries ({season} {year}).")
    return results


def extract_anilist_cover(media: dict) -> str:
    """Pull the best available cover URL from an AniList media object."""
    img = media.get("coverImage", {})
    return img.get("extraLarge") or img.get("large") or ""


def current_season_and_year() -> tuple[str, int]:
    """Return (ANILIST_SEASON_STRING, year) for today's date."""
    import datetime
    now   = datetime.date.today()
    month = now.month
    year  = now.year
    if month in (1, 2, 3):
        season = "WINTER"
    elif month in (4, 5, 6):
        season = "SPRING"
    elif month in (7, 8, 9):
        season = "SUMMER"
    else:
        season = "FALL"
    return season, year


# ──────────────────────────────────────────────
# MERGE LOGIC
# ──────────────────────────────────────────────
def merge_into_database(db: dict, new_entries: list[dict]) -> dict:
    """
    Merge a list of fully-resolved entry dicts into the existing database.

    Key rules
    ---------
    1. mal_id is the primary key; entries with the same mal_id are updated,
       never duplicated.
    2. Jikan cover_url always wins over AniList cover_url.
    3. anilist_id is back-filled if we previously lacked it.
    4. Old entries that are NOT in new_entries are kept untouched (incremental).
    """
    for entry in new_entries:
        key = str(entry["mal_id"])
        if key in db:
            existing = db[key]
            # Only overwrite cover if existing source is AniList (lower priority)
            if existing.get("source_used") == "AniList" and entry.get("source_used") == "Jikan":
                existing["cover_url"]   = entry["cover_url"]
                existing["source_used"] = "Jikan"
            # Back-fill anilist_id if we have it now
            if entry.get("anilist_id") and not existing.get("anilist_id"):
                existing["anilist_id"] = entry["anilist_id"]
            # Always keep the most complete title
            if entry.get("title") and entry["title"] != "Unknown":
                existing["title"] = entry["title"]
        else:
            db[key] = entry

    return db


# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("  Anime Cover Database — Sync Starting")
    print("=" * 60)

    # 1. Load existing database
    db = load_database()
    print(f"[DB] Loaded {len(db)} existing entries.")

    # 2. Fetch Jikan seasonal anime (primary source)
    jikan_raw = fetch_jikan_season_now()
    jikan_entries: list[dict] = []

    for raw in jikan_raw:
        entry = parse_jikan_entry(raw)
        if entry:
            jikan_entries.append(entry)

    print(f"[Jikan] Parsed {len(jikan_entries)} valid entries.")

    # 3. For each Jikan entry, try to enrich with AniList ID + cover fallback
    for i, entry in enumerate(jikan_entries):
        title = entry["title"]
        print(f"[AniList] ({i+1}/{len(jikan_entries)}) Searching: {title!r}")

        time.sleep(ANILIST_SLEEP)
        media = search_anilist_by_title(title)

        if media:
            entry["anilist_id"] = str(media["id"])
            # Only use AniList cover if Jikan returned nothing
            if not entry["cover_url"]:
                al_cover = extract_anilist_cover(media)
                if al_cover:
                    entry["cover_url"]   = al_cover
                    entry["source_used"] = "AniList"

        # If still no cover at all, mark clearly
        if not entry["cover_url"]:
            entry["source_used"] = "none"

    # 4. Fetch AniList seasonal data to catch shows Jikan may have missed
    season, year = current_season_and_year()
    print(f"\n[AniList] Fetching full seasonal list: {season} {year}")
    al_seasonal = fetch_anilist_season(season, year)

    # Build a normalised-title → mal_id index from everything we have so far
    existing_norm_titles: dict[str, str] = {
        normalize_title(e["title"]): k
        for k, e in db.items()
    }
    # Also index the freshly fetched Jikan entries
    for e in jikan_entries:
        existing_norm_titles[normalize_title(e["title"])] = e["mal_id"]

    # Add AniList-only entries (shows Jikan missed)
    anilist_only_entries: list[dict] = []

    for media in al_seasonal:
        al_titles = [
            media["title"].get("english") or "",
            media["title"].get("romaji") or "",
            media["title"].get("native") or "",
        ]
        best_title = next((t for t in al_titles if t), "Unknown")
        norm        = normalize_title(best_title)

        # Check if this AniList show already exists via any of its titles
        already_indexed = any(
            normalize_title(t) in existing_norm_titles
            for t in al_titles if t
        )
        if already_indexed:
            continue  # Already covered by Jikan — skip

        # New show found only on AniList
        al_cover = extract_anilist_cover(media)
        if not al_cover:
            continue  # Nothing useful; skip

        # We don't have a MAL ID for AniList-only entries.
        # Use a synthetic key: "AL-<anilist_id>"
        synthetic_key = f"AL-{media['id']}"

        new_entry = {
            "title":       best_title,
            "mal_id":      None,           # unknown
            "anilist_id":  str(media["id"]),
            "cover_url":   al_cover,
            "source_used": "AniList",
        }
        # Store under synthetic key temporarily; merge will handle it
        anilist_only_entries.append({**new_entry, "mal_id": synthetic_key})
        existing_norm_titles[norm] = synthetic_key

    print(f"[AniList] {len(anilist_only_entries)} additional anime not in Jikan.")

    # 5. Merge everything into the database
    all_new = jikan_entries + anilist_only_entries
    db = merge_into_database(db, all_new)

    # 6. Persist
    save_database(db)

    # 7. Summary
    jikan_count  = sum(1 for e in db.values() if e.get("source_used") == "Jikan")
    anilist_count = sum(1 for e in db.values() if e.get("source_used") == "AniList")
    none_count   = sum(1 for e in db.values() if e.get("source_used") == "none")
    print("\n── Summary ──────────────────────────────────────")
    print(f"  Total entries : {len(db)}")
    print(f"  Source = Jikan  : {jikan_count}")
    print(f"  Source = AniList: {anilist_count}")
    print(f"  No cover found  : {none_count}")
    print("─────────────────────────────────────────────────\n")
    print("Done ✓")


if __name__ == "__main__":
    main()
