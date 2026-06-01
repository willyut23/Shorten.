# shorten — A Self-Hosted URL Shortener

**Paste long. Get short.**

A self-hosted URL shortener that runs entirely on your machine. No accounts, no cloud, no tracking. Just a clean dark interface and a local database.

---

## ✨ Features

- **Instant shortening** — 6-character alphanumeric codes
- **Duplicate detection** — same URL always produces the same code
- **Persistent storage** — SQLite database saved alongside the script
- **Recent history** — last 10 shortened links displayed on the homepage
- **One-click copy** — copy any short link to your clipboard instantly
- **Click tracking** — every redirect is counted
- **Stats page** — total links and last-hour activity at `/stats`
- **Rate limiting** — max 10 shortens per minute per IP
- **CSRF protection** — built-in, no extra dependencies
- **Dark, minimal UI** — works great on desktop and mobile

---

## 📦 Setup

**Requirements:** Python 3.7 or later. No other dependencies needed — Flask installs automatically on first run.

    cd ~/Downloads
    python url_shortener.py

Then open your browser to:

    http://127.0.0.1:5000

---

## 🚀 Usage

| Action | How |
|---|---|
| Shorten a URL | Paste into the input, hit **Shorten** |
| Visit a short link | Go to `http://localhost:5000/xxxxxx` |
| Copy a link | Click the **copy** button next to any recent link |
| View stats | Navigate to `http://localhost:5000/stats` |
| Stop the server | `Ctrl + C` in the terminal |

---

## 📁 Project Structure

    url_shortener.py   ← the entire app (just run this file)
    urls.db            ← auto-created on first run

---

## ⚠️ Notes

- Links are only accessible while the server is running
- Short links use `localhost` — they won't work on other devices unless you expose the server (see below)
- To make the service available on your local network, edit the script and replace `app.run(...)` with:

      app.run(host='0.0.0.0', port=5000)

---

## 📄 License

This project is open source and provided as-is for personal use and learning.

---

Made by **Willyut**
