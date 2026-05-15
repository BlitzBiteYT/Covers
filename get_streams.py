#!/usr/bin/env python3
"""
anipy-seasonal-streams — get_streams.py
Fetches all streaming links (every quality) for every episode of every anime
in a given season + year using anipy-api's AllAnime provider.

Usage:
    python get_streams.py --season FALL --year 2024 [--lang sub] [--ep-limit 3] [--output streams.json]

Outputs a JSON file (and prints a summary table to stdout).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from anipy_api.provider import get_provider
    from anipy_api.provider.filter import Filters, FilterCapabilities, Season, MediaType
    from anipy_api.provider.base import LanguageTypeEnum
    from anipy_api.anime import Anime
except ImportError:
    sys.exit(
        "ERROR: anipy-api is not installed.\n"
        "Install it with:  pip install anipy-api\n"
    )

# ── Constants ────────────────────────────────────────────────────────────────

SEASON_MAP = {
    "SPRING": Season.SPRING,
    "SUMMER": Season.SUMMER,
    "FALL":   Season.FALL,
    "WINTER": Season.WINTER,
}

LANG_MAP = {
    "sub": LanguageTypeEnum.SUB,
    "dub": LanguageTypeEnum.DUB,
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def build_filters(season_str: str, year: int) -> Filters:
    season = SEASON_MAP.get(season_str.upper())
    if season is None:
        sys.exit(f"ERROR: unknown season '{season_str}'. Use SPRING/SUMMER/FALL/WINTER.")
    return Filters(year=year, season=season)


def resolve_lang(provider, anime_obj: Anime, preferred: str) -> LanguageTypeEnum | None:
    """Return the best available language for an anime."""
    lang_enum = LANG_MAP.get(preferred.lower(), LanguageTypeEnum.SUB)
    if lang_enum in anime_obj.languages:
        return lang_enum
    # fallback: take whatever is available
    if anime_obj.languages:
        return next(iter(anime_obj.languages))
    return None


def streams_for_episode(anime_obj: Anime, episode, lang: LanguageTypeEnum) -> list[dict]:
    """Return a list of stream dicts for one episode, sorted best→worst quality."""
    try:
        streams = anime_obj.get_videos(episode, lang)
    except Exception as exc:  # noqa: BLE001
        print(f"    ⚠  Could not fetch streams for ep {episode}: {exc}", file=sys.stderr)
        return []

    results = []
    for s in reversed(streams):          # get_videos() returns ascending; flip to best-first
        entry = {
            "url":        s.url,
            "resolution": s.resolution,  # width in px, e.g. 1920
            "quality":    f"{s.resolution}p" if s.resolution else "unknown",
            "language":   lang.value,
            "referrer":   s.referrer or "",
        }
        if s.subtitle:
            entry["subtitles"] = {
                code: {
                    "url":   sub.url,
                    "codec": sub.codec,
                    "lang":  sub.lang,
                }
                for code, sub in s.subtitle.items()
            }
        results.append(entry)
    return results


# ── Core logic ───────────────────────────────────────────────────────────────

def fetch_seasonal_streams(
    season_str: str,
    year: int,
    lang_pref: str = "sub",
    ep_limit: int | None = None,
    anime_limit: int | None = None,
) -> dict:
    """
    Main entry-point.  Returns a structured dict:

    {
      "meta": { season, year, lang, generated_at, provider },
      "anime": [
        {
          "name": "...",
          "identifier": "...",
          "languages": [...],
          "episodes": [
            {
              "episode": 1,
              "streams": [
                { "url": "...", "resolution": 1920, "quality": "1920p", ... }
              ]
            }
          ]
        }
      ]
    }
    """
    print(f"\n{'─'*60}")
    print(f"  anipy-seasonal-streams")
    print(f"  Season: {season_str.upper()}  Year: {year}  Lang: {lang_pref.upper()}")
    print(f"{'─'*60}\n")

    provider = get_provider("allanime")
    if provider is None:
        sys.exit("ERROR: AllAnime provider not found — check your anipy-api installation.")

    filters = build_filters(season_str, year)

    print("⏳  Searching for anime …")
    try:
        results = provider.get_search("", filters=filters)
    except Exception as exc:
        sys.exit(f"ERROR: search failed — {exc}")

    if not results:
        print("⚠  No anime found for this season/year combination.")
        return {
            "meta": {
                "season": season_str.upper(),
                "year": year,
                "lang": lang_pref,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "provider": "allanime",
            },
            "anime": [],
        }

    if anime_limit:
        results = results[:anime_limit]

    print(f"✅  Found {len(results)} titles.\n")

    output_anime = []

    for idx, result in enumerate(results, 1):
        anime_obj = Anime.from_search_result(provider, result)
        print(f"[{idx:>3}/{len(results)}] {anime_obj.name}")

        lang = resolve_lang(provider, anime_obj, lang_pref)
        if lang is None:
            print("          ⚠  no supported language — skipping")
            continue

        try:
            episodes = anime_obj.get_episodes(lang)
        except Exception as exc:
            print(f"          ⚠  could not fetch episodes: {exc}", file=sys.stderr)
            continue

        if ep_limit:
            episodes = episodes[:ep_limit]

        print(f"          ↳  {len(episodes)} episode(s) [{lang.value}]")

        anime_entry = {
            "name":       anime_obj.name,
            "identifier": anime_obj.identifier,
            "languages":  [l.value for l in anime_obj.languages],
            "episodes":   [],
        }

        for ep in episodes:
            streams = streams_for_episode(anime_obj, ep, lang)
            qualities = [s["quality"] for s in streams]
            print(f"             ep {ep:>4}  →  {', '.join(qualities) or 'no streams'}")
            anime_entry["episodes"].append({
                "episode": ep,
                "streams": streams,
            })

        output_anime.append(anime_entry)

    print(f"\n{'─'*60}")
    print(f"  Done!  {len(output_anime)} anime processed.")
    print(f"{'─'*60}\n")

    return {
        "meta": {
            "season":       season_str.upper(),
            "year":         year,
            "lang":         lang_pref,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "provider":     "allanime",
        },
        "anime": output_anime,
    }


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Fetch all streaming links (every quality) for a seasonal anime lineup."
    )
    p.add_argument(
        "--season", "-s",
        required=True,
        choices=["SPRING", "SUMMER", "FALL", "WINTER"],
        type=str.upper,
        help="Anime season (SPRING | SUMMER | FALL | WINTER)",
    )
    p.add_argument(
        "--year", "-y",
        required=True,
        type=int,
        help="4-digit year, e.g. 2024",
    )
    p.add_argument(
        "--lang", "-l",
        default="sub",
        choices=["sub", "dub"],
        help="Preferred language (default: sub)",
    )
    p.add_argument(
        "--ep-limit",
        type=int,
        default=None,
        metavar="N",
        help="Only fetch the first N episodes per anime (useful for testing)",
    )
    p.add_argument(
        "--anime-limit",
        type=int,
        default=None,
        metavar="N",
        help="Only process the first N anime returned by the season search",
    )
    p.add_argument(
        "--output", "-o",
        default="streams.json",
        help="Output JSON file path (default: streams.json)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    data = fetch_seasonal_streams(
        season_str=args.season,
        year=args.year,
        lang_pref=args.lang,
        ep_limit=args.ep_limit,
        anime_limit=args.anime_limit,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"📄  Output saved to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
