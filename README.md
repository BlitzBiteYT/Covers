# 🎌 Anime Cover Database — Full Setup Guide

A self-updating anime cover database that pulls from **Jikan (MyAnimeList)** and **AniList**, stores everything in `database.json`, and auto-commits changes to GitHub every day via GitHub Actions.

---

## 📋 Table of Contents

- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Prerequisites](#-prerequisites)
- [Part 1 — GitHub Repository Setup](#-part-1--github-repository-setup)
- [Part 2 — Enable GitHub Actions Write Permissions](#-part-2--enable-github-actions-write-permissions)
- [Part 3 — Running Manually on Termux (Android)](#-part-3--running-manually-on-termux-android)
- [Part 4 — Running on a Regular Linux / macOS Machine](#-part-4--running-on-a-regular-linux--macos-machine)
- [Part 5 — Running on Windows](#-part-5--running-on-windows)
- [Part 6 — Running on a VPS / Server (Automated)](#-part-6--running-on-a-vps--server-automated)
- [Understanding the Output](#-understanding-the-output)
- [Customisation](#-customisation)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)

---

## 📁 Project Structure

After setup your repository should look like this:

```
your-repo/
├── scraper.py                    ← Main sync script
├── database.json                 ← Auto-generated on first run
├── requirements.txt              ← Python dependencies (optional)
└── .github/
    └── workflows/
        └── update.yml            ← GitHub Actions automation
```

---

## ⚙️ How It Works

```
┌─────────────────────────────────────────────────────────┐
│                      scraper.py                         │
│                                                         │
│  Step 1: Fetch all pages of Jikan /seasons/now          │
│             ↓                                           │
│  Step 2: For each show, search AniList by title         │
│          to get the AniList ID and a fallback cover     │
│             ↓                                           │
│  Step 3: Fetch AniList's own seasonal list to           │
│          catch any shows Jikan missed                   │
│             ↓                                           │
│  Step 4: Merge everything into database.json            │
│          (Jikan cover wins · old entries kept)          │
└─────────────────────────────────────────────────────────┘
```

**Priority rule:** Jikan (MAL) cover URL is always preferred. AniList's `extraLarge` cover is only used when Jikan returns no image.

---

## 🔧 Prerequisites

| Requirement | Why |
|---|---|
| Python 3.10 or newer | Script uses modern type hints |
| `requests` library | HTTP calls to both APIs |
| A GitHub account | To host the repo and run Actions |
| Git (any version) | To push files to GitHub |

No API keys are needed. Both Jikan and AniList have free public access.

---

## 🐙 Part 1 — GitHub Repository Setup

### Step 1.1 — Create a new repository

1. Go to [github.com/new](https://github.com/new)
2. Give it a name, e.g. `anime-cover-db`
3. Set it to **Public** or **Private** (Actions work either way)
4. Check **"Add a README file"** (so the repo isn't empty)
5. Click **"Create repository"**

### Step 1.2 — Upload your files

**Option A — Via the GitHub website (easiest)**

1. On your new repo page click **"Add file" → "Upload files"**
2. Upload `scraper.py`
3. Click **"Commit changes"**
4. Repeat for the workflow file — but first you must create the folder path:
   - Click **"Add file" → "Create new file"**
   - In the filename box type exactly: `.github/workflows/update.yml`
   - GitHub auto-creates the folders as you type the slashes
   - Paste the contents of `update.yml` into the editor
   - Click **"Commit changes"**

**Option B — Via Git on your computer / Termux**

```bash
# Clone the empty repo (replace with your actual URL)
git clone https://github.com/YOUR_USERNAME/anime-cover-db.git
cd anime-cover-db

# Copy your files in
cp /path/to/scraper.py .
mkdir -p .github/workflows
cp /path/to/update.yml .github/workflows/

# Push everything
git add .
git commit -m "feat: initial scraper setup"
git push
```

---

## 🔐 Part 2 — Enable GitHub Actions Write Permissions

This is the most important step. Without it the workflow will fail with a `403` error when trying to commit `database.json`.

### Step 2.1 — Change the default workflow permission

1. Open your repository on GitHub
2. Click the **"Settings"** tab (top navigation bar, rightmost)
3. In the left sidebar scroll down to **"Actions"** and click it
4. Click **"General"** (the sub-item under Actions)
5. Scroll down to **"Workflow permissions"**
6. Select **"Read and write permissions"**
7. Make sure **"Allow GitHub Actions to create and approve pull requests"** is also checked
8. Click **"Save"**

```
Settings
  └── Actions
        └── General
              └── Workflow permissions
                    ● Read and write permissions   ← select this
                    ○ Read repository contents and packages permissions
```

### Step 2.2 — Verify the workflow file path

The workflow MUST be at exactly this path in your repo:

```
.github/workflows/update.yml
```

A common mistake is placing it at `workflows/update.yml` (missing the `.github` parent). GitHub will silently ignore it.

### Step 2.3 — Trigger your first manual run

1. Click the **"Actions"** tab in your repo
2. You should see **"Update Anime Cover Database"** in the left sidebar
3. Click it, then click **"Run workflow" → "Run workflow"** (green button)
4. Watch the live log — the first run takes about 10–15 minutes

---

## 📱 Part 3 — Running Manually on Termux (Android)

Termux lets you run the script directly on your phone without needing a computer.

### Step 3.1 — Install Termux

> ⚠️ **Do NOT install Termux from the Google Play Store** — that version is outdated and unmaintained.

Install from **F-Droid** instead:
1. Go to [f-droid.org](https://f-droid.org) in your browser
2. Download and install the F-Droid APK
3. Open F-Droid, search for **"Termux"**, install it

### Step 3.2 — Initial Termux setup

Open Termux and run these commands one at a time:

```bash
# Update package lists
pkg update && pkg upgrade -y

# Install Python and Git
pkg install python git -y

# Install pip (Python package manager)
pip install --upgrade pip
```

### Step 3.3 — Install the requests library

```bash
pip install requests
```

If you see a warning about `--break-system-packages`, use:

```bash
pip install requests --break-system-packages
```

### Step 3.4 — Clone your GitHub repository

```bash
# Navigate to Termux home folder
cd ~

# Clone your repo (replace with your URL)
git clone https://github.com/YOUR_USERNAME/anime-cover-db.git

# Enter the project folder
cd anime-cover-db
```

### Step 3.5 — Run the scraper

```bash
python scraper.py
```

You'll see live output like:

```
============================================================
  Anime Cover Database — Sync Starting
============================================================
[DB] 'database.json' not found — starting fresh.
[Jikan] Fetching page 1 …
[Jikan] Fetching page 2 …
[Jikan] Fetched 48 seasonal anime.
[Jikan] Parsed 48 valid entries.
[AniList] (1/48) Searching: 'Mushoku Tensei II'
[AniList] (2/48) Searching: 'Oshi no Ko 2nd Season'
...
[DB] Saved 61 entries → 'database.json'

── Summary ──────────────────────────────────────
  Total entries : 61
  Source = Jikan  : 44
  Source = AniList: 17
  No cover found  : 0
─────────────────────────────────────────────────
Done ✓
```

### Step 3.6 — Push results back to GitHub

```bash
# Configure Git with your details (only needed once)
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Stage, commit, and push
git add database.json
git commit -m "chore: initial database sync"
git push
```

Git will ask for your GitHub username and password. Use a **Personal Access Token** instead of your password:

1. On GitHub go to **Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **"Generate new token (classic)"**
3. Give it a name, set expiry, and tick the **"repo"** scope
4. Copy the token — paste it as your password in Termux

### Step 3.7 — Automate on Termux with cron (optional)

If you want Termux itself to run the script daily (independent of GitHub Actions):

```bash
# Install cron in Termux
pkg install cronie termux-services -y

# Start the cron service
sv-enable crond
sv up crond

# Open the crontab editor
crontab -e
```

Add this line to run every day at 7 AM:

```
0 7 * * * cd ~/anime-cover-db && python scraper.py && git add database.json && git commit -m "auto sync" && git push
```

Save and exit (press `Ctrl+X`, then `Y`, then `Enter` if using nano).

---

## 🖥️ Part 4 — Running on a Regular Linux / macOS Machine

### Step 4.1 — Install Python

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install python3 python3-pip git -y
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install python3 python3-pip git -y
```

**macOS (using Homebrew):**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and Git
brew install python git
```

### Step 4.2 — Clone and run

```bash
git clone https://github.com/YOUR_USERNAME/anime-cover-db.git
cd anime-cover-db

# Install dependency
pip3 install requests

# Run
python3 scraper.py
```

### Step 4.3 — Automate with cron (Linux/macOS)

```bash
# Open crontab
crontab -e

# Run every day at 6 AM
0 6 * * * cd /path/to/anime-cover-db && python3 scraper.py && git add database.json && git commit -m "auto sync" && git push >> /tmp/anime-sync.log 2>&1
```

---

## 🪟 Part 5 — Running on Windows

### Step 5.1 — Install Python

1. Go to [python.org/downloads](https://python.org/downloads)
2. Download the latest Python 3.x installer
3. Run it — **check "Add Python to PATH"** before clicking Install
4. Verify: open Command Prompt and run `python --version`

### Step 5.2 — Install Git

1. Go to [git-scm.com/download/win](https://git-scm.com/download/win)
2. Download and install Git for Windows (use defaults)

### Step 5.3 — Clone and run

Open **Command Prompt** or **PowerShell**:

```powershell
git clone https://github.com/YOUR_USERNAME/anime-cover-db.git
cd anime-cover-db

pip install requests

python scraper.py
```

### Step 5.4 — Automate with Task Scheduler (Windows)

1. Press `Win + S`, search **"Task Scheduler"**, open it
2. Click **"Create Basic Task"** in the right panel
3. Name it `Anime Cover Sync`, click Next
4. Choose **"Daily"**, click Next
5. Set your preferred start time, click Next
6. Choose **"Start a program"**, click Next
7. In **"Program/script"** enter: `python`
8. In **"Add arguments"** enter: `scraper.py`
9. In **"Start in"** enter the full path to your repo folder, e.g.: `C:\Users\YourName\anime-cover-db`
10. Click Finish

---

## 🌐 Part 6 — Running on a VPS / Server (Automated)

If you have a Linux VPS (DigitalOcean, Linode, AWS EC2, etc.):

### Step 6.1 — First-time setup

```bash
# SSH into your server
ssh user@your-server-ip

# Install tools
sudo apt update && sudo apt install python3 python3-pip git -y

# Clone repo
git clone https://github.com/YOUR_USERNAME/anime-cover-db.git
cd anime-cover-db
pip3 install requests

# Configure Git
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### Step 6.2 — Store GitHub credentials safely

```bash
# Cache credentials for 24 hours
git config --global credential.helper 'cache --timeout=86400'

# Or store permanently (less secure, fine for a private server)
git config --global credential.helper store
```

Then do one `git push` manually and enter your token — it gets saved for future pushes.

### Step 6.3 — Set up cron on the server

```bash
crontab -e

# Add — runs daily at 6:00 AM UTC
0 6 * * * cd /home/user/anime-cover-db && python3 scraper.py >> /var/log/anime-sync.log 2>&1 && git add database.json && git commit -m "auto sync $(date)" && git push >> /var/log/anime-sync.log 2>&1
```

### Step 6.4 — Monitor logs

```bash
# Watch the log in real time
tail -f /var/log/anime-sync.log

# Check the last sync
tail -50 /var/log/anime-sync.log
```

---

## 📊 Understanding the Output

### database.json format

Each entry in the JSON array looks like this:

```json
{
  "title": "Dungeon Meshi",
  "mal_id": "52701",
  "anilist_id": "153518",
  "cover_url": "https://cdn.myanimelist.net/images/anime/1...jpg",
  "source_used": "Jikan"
}
```

| Field | Description |
|---|---|
| `title` | English title (falls back to romaji, then Japanese) |
| `mal_id` | MyAnimeList ID — primary key. `null` for AniList-only entries, prefixed with `AL-` |
| `anilist_id` | AniList ID — filled in when found, otherwise `null` |
| `cover_url` | Direct URL to the cover image |
| `source_used` | `"Jikan"`, `"AniList"`, or `"none"` |

### Useful one-liners to inspect the database

```bash
# Count total entries
python3 -c "import json; d=json.load(open('database.json')); print(len(d))"

# Count by source
grep -c '"source_used": "Jikan"' database.json
grep -c '"source_used": "AniList"' database.json

# Find entries with no cover
python3 -c "
import json
for e in json.load(open('database.json')):
    if e['source_used'] == 'none':
        print(e['title'])
"

# List all titles
python3 -c "
import json
for e in json.load(open('database.json')):
    print(e['title'])
"

# Find a specific anime
python3 -c "
import json
q = 'frieren'
for e in json.load(open('database.json')):
    if q.lower() in e['title'].lower():
        print(e)
"
```

---

## 🎛️ Customisation

### Change the sync schedule

Edit the `cron` line in `update.yml`:

```yaml
# Every day at 06:00 UTC (default)
- cron: "0 6 * * *"

# Every 12 hours
- cron: "0 */12 * * *"

# Every Monday at 08:00 UTC
- cron: "0 8 * * 1"
```

Use [crontab.guru](https://crontab.guru) to build cron expressions visually.

### Change the sleep timers

In `scraper.py` at the top of the file:

```python
JIKAN_SLEEP   = 1.5   # seconds between Jikan page requests
ANILIST_SLEEP = 0.7   # seconds between AniList requests
```

Increase these if you're getting rate-limit errors (HTTP 429). Do not set `JIKAN_SLEEP` below `1.0` — Jikan's public limit is 3 requests/second.

### Fetch a different season

By default the script uses the *current* season. To hardcode a specific season, edit the bottom of `main()` in `scraper.py`:

```python
# Replace this:
season, year = current_season_and_year()

# With this (example — Spring 2024):
season, year = "SPRING", 2024
```

AniList season strings: `"WINTER"`, `"SPRING"`, `"SUMMER"`, `"FALL"`

---

## 🐛 Troubleshooting

### "Permission denied" when pushing from Termux

You need a Personal Access Token (PAT), not your password.
- GitHub: **Settings → Developer settings → Personal access tokens → Generate new token**
- Scope required: `repo` (Full control of private repositories)
- Use the token as the password when `git push` asks

### GitHub Actions fails with "Resource not accessible by integration"

You forgot to enable write permissions. Go back to [Part 2](#-part-2--enable-github-actions-write-permissions) and ensure **"Read and write permissions"** is selected.

### Jikan returns 429 (Too Many Requests)

Increase `JIKAN_SLEEP` to `2.5` or higher:
```python
JIKAN_SLEEP = 2.5
```

### AniList returns 429

Increase `ANILIST_SLEEP`:
```python
ANILIST_SLEEP = 1.5
```

### `database.json` shows `"source_used": "none"` for some entries

This means neither API returned a cover for that show. It's rare — usually affects very obscure or newly announced titles. The entry is still stored so it can be updated in future runs.

### Script runs but `database.json` is empty or not created

Check that the script has **write permission** to the current folder:

```bash
# Linux/Termux/macOS
ls -la database.json   # should exist after a run
touch database.json    # creates it manually if missing
```

### `ModuleNotFoundError: No module named 'requests'`

The `requests` library isn't installed in the Python environment being used:

```bash
# Standard
pip install requests

# If that fails (Termux or system Python)
pip install requests --break-system-packages

# If multiple Python versions exist
python3 -m pip install requests
```

### Workflow doesn't appear in the Actions tab

The file is in the wrong location. It must be at:
```
.github/workflows/update.yml
```
Check for typos — `.github` starts with a dot, and the folder is `workflows` (plural).

---

## ❓ FAQ

**Q: Will running the script delete my old anime entries?**
No. The merge logic is additive. Old entries are never deleted — only updated if better data is available.

**Q: What if I run it twice in a row?**
It's idempotent. Running it multiple times produces the same result. GitHub Actions will only commit if `database.json` actually changed.

**Q: Can I use this for past seasons too?**
Yes — change `season` and `year` in `main()` to any past season and run the script. Old entries will be added to your database and kept in future runs.

**Q: Why is `mal_id` a string, not a number?**
JSON numbers have precision limits with large integers. Using strings avoids any risk of IDs being mangled and makes lookup by key consistent.

**Q: The GitHub Actions run takes 15+ minutes — is that normal?**
Yes. The script sleeps between each API call to avoid rate limits. A typical season has 40–70 shows, and each requires two API calls (Jikan + AniList search). Budget about 1–2 seconds per show plus page fetch time.

**Q: Do I need to keep Termux open while the script runs?**
If you're running it manually in Termux, yes — the session must stay active. To run it in the background even after closing Termux, use `nohup`:

```bash
nohup python scraper.py > sync.log 2>&1 &
# Check progress
tail -f sync.log
```

**Q: What's the difference between GitHub Actions and running locally?**
They're identical code-wise. GitHub Actions just runs the script on GitHub's servers on a schedule and auto-commits the result, so you never have to think about it after setup.
