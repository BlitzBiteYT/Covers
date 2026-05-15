# 📺 anipy-seasonal-streams

> Fetch **every streaming link at every quality** for every episode in a seasonal anime lineup — powered by [anipy-api](https://github.com/sdaqo/anipy-cli) and GitHub Actions.

---

## What it does

Given a **season** (SPRING / SUMMER / FALL / WINTER) and a **year**, this tool:

1. Queries the **AllAnime** provider for all titles airing that season.
2. For each title, fetches every episode available.
3. For each episode, collects **all stream URLs at every resolution** (1080p, 720p, 480p, 360p …).
4. Saves everything to a single structured **JSON file**.

The GitHub Actions workflow runs automatically on a schedule (1st of each new season) or on-demand via `workflow_dispatch` with a simple UI.

---

## Output format

```json
{
  "meta": {
    "season": "FALL",
    "year": 2024,
    "lang": "sub",
    "generated_at": "2024-10-01T04:12:33Z",
    "provider": "allanime"
  },
  "anime": [
    {
      "name": "Some Anime Title",
      "identifier": "abc123",
      "languages": ["sub", "dub"],
      "episodes": [
        {
          "episode": 1,
          "streams": [
            {
              "url": "https://…/1080/index.m3u8",
              "resolution": 1920,
              "quality": "1920p",
              "language": "sub",
              "referrer": "https://…",
              "subtitles": {
                "en": { "url": "…", "codec": "vtt", "lang": "en" }
              }
            },
            {
              "url": "https://…/720/index.m3u8",
              "resolution": 1280,
              "quality": "1280p",
              "language": "sub"
            }
          ]
        }
      ]
    }
  ]
}
```

Each `streams` array is sorted **best quality → worst quality**.

---

## Quick start (local)

```bash
# 1. Clone
git clone https://github.com/<you>/anipy-seasonal-streams
cd anipy-seasonal-streams

# 2. Install (Python 3.10+ required)
pip install -r requirements.txt

# 3. Run
python get_streams.py --season FALL --year 2024 --lang sub

# Optional flags
python get_streams.py \
  --season   FALL       \   # SPRING | SUMMER | FALL | WINTER
  --year     2024       \   # 4-digit year
  --lang     sub        \   # sub | dub
  --ep-limit 3          \   # only first 3 episodes per anime (great for testing)
  --anime-limit 10      \   # only first 10 anime returned
  --output   out.json       # output path (default: streams.json)
```

---

## GitHub Actions workflow

### On-demand (recommended)

1. Go to **Actions → Fetch Seasonal Anime Streams → Run workflow**.
2. Fill in the inputs:

   | Input | Description | Default |
   |-------|-------------|---------|
   | `season` | SPRING / SUMMER / FALL / WINTER | FALL |
   | `year` | 4-digit year | 2024 |
   | `lang` | `sub` or `dub` | sub |
   | `ep_limit` | Max episodes per anime (blank = all) | — |
   | `anime_limit` | Max titles to process (blank = all) | — |

3. When the run finishes, download the **artifact** from the run summary page.  
   The artifact is named e.g. `streams-FALL-2024-sub` and contains:
   - `streams_FALL_2024_sub.json` — full data
   - `summary.md` — human-readable table

### Scheduled runs

The workflow automatically fires on the **1st of every quarter** at 04:00 UTC:

| Date | Season fetched |
|------|---------------|
| Jan 1 | WINTER |
| Apr 1 | SPRING |
| Jul 1 | SUMMER |
| Oct 1 | FALL |

Artifacts are retained for **90 days**.

### (Optional) Commit results back to the repo

Uncomment the last step in `.github/workflows/fetch_streams.yml` to push results to a `results` branch automatically. Requires:
- **Settings → Actions → General → Workflow permissions** set to **Read and write**.

---

## Architecture

```
anipy-seasonal-streams/
├── get_streams.py                        # Core fetch script
├── requirements.txt                      # anipy-api dependency
├── .github/
│   └── workflows/
│       └── fetch_streams.yml            # GitHub Actions workflow
└── output/                              # Generated files (git-ignored)
    ├── streams_FALL_2024_sub.json
    └── summary.md
```

### Data flow

```
workflow_dispatch / schedule
        │
        ▼
  resolve_season_year()
        │
        ▼
  get_provider("allanime")
        │
        ▼
  provider.get_search("", Filters(season=…, year=…))   ← AllAnime GraphQL
        │
        ├─ for each ProviderSearchResult
        │       │
        │       ▼
        │   Anime.from_search_result()
        │       │
        │       ▼
        │   anime.get_episodes(lang)
        │       │
        │       ├─ for each episode
        │       │       │
        │       │       ▼
        │       │   anime.get_videos(episode, lang)   ← all quality streams
        │       │       │
        │       │       ▼
        │       │   collect ProviderStream objects
        │
        ▼
  streams_SEASON_YEAR_LANG.json
```

---

## Caveats

- **AllAnime only** — this project targets the AllAnime provider because it is the only one that supports both `season` and `year` filters (`FilterCapabilities.SEASON | YEAR`). AnimeKai and the native provider do not support season browsing.
- Stream URLs are **ephemeral** — they expire (typically within hours to a day). Re-run the workflow to get fresh URLs.
- Large seasonal lineups (40+ titles × 12 episodes) can take **30–60 minutes**. Use `--anime-limit` / `--ep-limit` in the workflow inputs to scope down a run.
- anipy-api must be installed from **PyPI** (`pip install anipy-api`); no extra config is needed for AllAnime.

---

## License

GPL-3.0 — same as the upstream [anipy-cli](https://github.com/sdaqo/anipy-cli) project this depends on.

> **DISCLAIMER**: This tool accesses publicly available streams. Users are responsible for compliance with their local laws. This project does not endorse or condone copyright infringement.
