# shorten.
It's a self-hosted URL shortener you run locally on your computer.
# shorten.

**Paste long. Get short.**

A self-hosted URL shortener that runs entirely on your machine. No accounts, no cloud, no tracking. Just a clean dark interface and a local database.

---

## What it does

Paste any URL — no matter how long — and get a short 6-character link back instantly. Visit the short link and you're redirected to the original. Everything is saved locally so your links survive restarts.

---

## Setup

**Requirements:** Python 3.7+. That's it.

```bash
cd ~/Downloads
python url_shortener.py
```

Flask will auto-install on first run if it's not already present. Then open your browser to:

```
http://127.0.0.1:5000
```

---

## Features

- **Instant shortening** — 6-character alphanumeric codes
- **Duplicate detection** — paste the same URL twice, get the same code back
- **Persistent storage** — SQLite database saved alongside the script
- **Recent history** — last 10 shortened links shown on the homepage
- **One-click copy** — copy any short link to clipboard instantly
- **Click tracking** — every redirect is counted
- **Stats page** — total links and last-hour activity at `/stats`
- **Rate limiting** — max 10 shortens per minute per IP
- **CSRF protection** — built-in, no extra dependencies

---

## Usage

| Action | How |
|---|---|
| Shorten a URL | Paste into the input, hit **Shorten** |
| Visit a short link | Go to `http://localhost:5000/xxxxxx` |
| Copy a link | Click the **copy** button next to any recent link |
| View stats | Navigate to `http://localhost:5000/stats` |
| Stop the server | `Ctrl + C` in the terminal |

---

## Project structure

```
url_shortener.py   ← the entire app (run this)
urls.db            ← auto-created on first run
```

---

## Notes

- Links are only accessible while the server is running
- Short links use `localhost` — they won't work on other devices unless you expose the server on your network
- To share on a local network, run with `app.run(host='0.0.0.0', port=5000)` inside the script

---

Made by **Willyut**
