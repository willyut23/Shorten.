import sys
import subprocess
import os

# ─── Auto-install Flask if missing ───────────────────────────────────────────
try:
    import flask
except ImportError:
    print("Flask not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"], stdout=subprocess.DEVNULL)
    print("Flask installed successfully!\n")

# ─── Imports ──────────────────────────────────────────────────────────────────
import sqlite3
import random
import string
import hashlib
import time
import re
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
from flask import (
    Flask, request, redirect, url_for, flash,
    render_template_string, session, jsonify, g
)

# ─── ASCII Banner ─────────────────────────────────────────────────────────────
BANNER = r"""
█    ██  ██▀███   ██▓         ██████  ██░ ██  ▒█████   ██▀███  ▄▄▄█████▓▓█████  ███▄    █ 
██  ▓██▒▓██ ▒ ██▒▓██▒       ▒██    ▒ ▓██░ ██▒▒██▒  ██▒▓██ ▒ ██▒▓  ██▒ ▓▒▓█   ▀  ██ ▀█   █ 
▓██  ▒██░▓██ ░▄█ ▒▒██░       ░ ▓██▄   ▒██▀▀██░▒██░  ██▒▓██ ░▄█ ▒▒ ▓██░ ▒░▒███   ▓██  ▀█ ██▒
▓▓█  ░██░▒██▀▀█▄  ▒██░         ▒   ██▒░▓█ ░██ ▒██   ██░▒██▀▀█▄  ░ ▓██▓ ░ ▒▓█  ▄ ▓██▒  ▐▌██▒
▒▒█████▓ ░██▓ ▒██▒░██████▒   ▒██████▒▒░▓█▒░██▓░ ████▓▒░░██▓ ▒██▒  ▒██▒ ░ ░▒████▒▒██░   ▓██░
░▒▓▒ ▒ ▒ ░ ▒▓ ░▒▓░░ ▒░▓  ░   ▒ ▒▓▒ ▒ ░ ▒ ░░▒░▒░ ▒░▒░▒░ ░ ▒▓ ░▒▓░  ▒ ░░   ░░ ▒░ ░░ ▒░   ▒ ▒ 
░░▒░ ░ ░   ░▒ ░ ▒░░ ░ ▒  ░   ░ ░▒  ░ ░ ▒ ░▒░ ░  ░ ▒ ▒░   ░▒ ░ ▒░    ░     ░ ░  ░░ ░░   ░ ▒░
 ░░░ ░ ░   ░░   ░   ░ ░      ░  ░  ░   ░  ░░ ░░ ░ ░ ▒    ░░   ░   ░         ░      ░   ░ ░ 
   ░        ░         ░  ░         ░   ░  ░  ░    ░ ░     ░                 ░  ░         ░ 
"""

print(BANNER)
print("  🔗  URL Shortener — Starting up...")
print("  Made By Willyut\n")

# ─── App Config ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(32)

DATABASE = "urls.db"
CHARS = string.ascii_letters + string.digits
RATE_LIMIT = 10        # max requests
RATE_WINDOW = 60       # per 60 seconds

# ─── Rate Limiting (in-memory) ────────────────────────────────────────────────
rate_data = defaultdict(list)

def is_rate_limited(ip):
    now = time.time()
    window_start = now - RATE_WINDOW
    rate_data[ip] = [t for t in rate_data[ip] if t > window_start]
    if len(rate_data[ip]) >= RATE_LIMIT:
        return True
    rate_data[ip].append(now)
    return False

# ─── Database Helpers ─────────────────────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            code      TEXT    UNIQUE NOT NULL,
            original  TEXT    NOT NULL,
            url_hash  TEXT    UNIQUE NOT NULL,
            created   DATETIME DEFAULT CURRENT_TIMESTAMP,
            hits      INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def generate_code():
    return ''.join(random.choices(CHARS, k=6))

def is_valid_url(url):
    pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))

def get_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = hashlib.sha256(os.urandom(32)).hexdigest()
    return session['csrf_token']

def csrf_protect(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'POST':
            token = request.form.get('csrf_token', '')
            if not token or token != session.get('csrf_token'):
                flash('Invalid request. Please try again.', 'error')
                return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── HTML Template ─────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>shorten — by Willyut</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:       #111113;
      --surface:  #1a1a1d;
      --border:   #2a2a2e;
      --border2:  #333338;
      --text:     #e2e2e6;
      --muted:    #6b6b72;
      --accent:   #e2e2e6;
      --link:     #a0a8ff;
      --success:  #5dba7d;
      --error:    #e05c5c;
      --info:     #7b9fe8;
    }

    html { font-size: 15px; }

    body {
      font-family: 'DM Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 4rem 1.25rem 5rem;
    }

    .wrapper { width: 100%; max-width: 580px; }

    /* ── Header ── */
    header { margin-bottom: 3rem; }
    .wordmark {
      font-family: 'IBM Plex Mono', monospace;
      font-size: 1rem;
      font-weight: 500;
      color: var(--text);
      letter-spacing: -.01em;
      display: flex;
      align-items: center;
      gap: .5rem;
    }
    .wordmark-dot { color: var(--muted); }
    .nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .nav-link {
      font-family: 'IBM Plex Mono', monospace;
      font-size: .75rem;
      color: var(--muted);
      text-decoration: none;
      transition: color .15s;
    }
    .nav-link:hover { color: var(--text); }

    /* ── Divider ── */
    hr {
      border: none;
      border-top: 1px solid var(--border);
      margin: 1.5rem 0;
    }

    /* ── Flash Messages ── */
    .flashes { list-style: none; margin-bottom: 1.25rem; }
    .flashes li {
      padding: .6rem .9rem;
      border-radius: 6px;
      font-size: .8rem;
      margin-bottom: .4rem;
      font-family: 'IBM Plex Mono', monospace;
      border-left: 3px solid;
      animation: fadeOut 0.4s ease 3.5s forwards;
    }
    .flashes .error   { background: rgba(224,92,92,.08);  border-color: var(--error);   color: #e08080; }
    .flashes .success { background: rgba(93,186,125,.08); border-color: var(--success); color: #7dd09a; }
    .flashes .info    { background: rgba(123,159,232,.08);border-color: var(--info);    color: #9ab5f0; }
    @keyframes fadeOut { to { opacity: 0; max-height: 0; padding: 0; margin: 0; overflow: hidden; } }

    /* ── Input area ── */
    .input-group {
      display: flex;
      gap: .5rem;
      align-items: stretch;
    }
    .input-group input[type="url"] {
      flex: 1;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 7px;
      color: var(--text);
      font-family: 'IBM Plex Mono', monospace;
      font-size: .85rem;
      padding: .7rem 1rem;
      outline: none;
      transition: border-color .15s;
      min-width: 0;
    }
    .input-group input[type="url"]:focus { border-color: var(--border2); }
    .input-group input[type="url"]::placeholder { color: var(--muted); }

    .btn-primary {
      background: var(--text);
      border: none;
      border-radius: 7px;
      color: var(--bg);
      cursor: pointer;
      font-family: 'DM Sans', sans-serif;
      font-size: .85rem;
      font-weight: 600;
      padding: .7rem 1.25rem;
      white-space: nowrap;
      transition: opacity .15s;
      flex-shrink: 0;
    }
    .btn-primary:hover { opacity: .85; }
    .btn-primary:active { opacity: .7; }

    /* ── Section heading ── */
    .section-label {
      font-family: 'IBM Plex Mono', monospace;
      font-size: .7rem;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: .85rem;
    }

    /* ── URL list ── */
    .url-list { display: flex; flex-direction: column; }

    .url-item {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: .75rem;
      padding: .75rem 0;
      border-bottom: 1px solid var(--border);
    }
    .url-item:last-child { border-bottom: none; }

    .short-link {
      font-family: 'IBM Plex Mono', monospace;
      font-size: .8rem;
      color: var(--link);
      text-decoration: none;
      white-space: nowrap;
      transition: opacity .15s;
    }
    .short-link:hover { opacity: .75; }

    .original-url {
      font-size: .78rem;
      color: var(--muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .copy-btn {
      background: transparent;
      border: 1px solid var(--border);
      border-radius: 5px;
      color: var(--muted);
      cursor: pointer;
      font-family: 'IBM Plex Mono', monospace;
      font-size: .7rem;
      padding: .28rem .6rem;
      transition: border-color .15s, color .15s;
      white-space: nowrap;
    }
    .copy-btn:hover { border-color: var(--border2); color: var(--text); }
    .copy-btn.copied { border-color: var(--success); color: var(--success); }

    /* ── Stats ── */
    .stats-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1px;
      background: var(--border);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }
    .stat-box {
      background: var(--surface);
      padding: 1.5rem 1.75rem;
    }
    .stat-box .num {
      font-family: 'IBM Plex Mono', monospace;
      font-size: 2rem;
      font-weight: 500;
      color: var(--text);
      line-height: 1;
    }
    .stat-box .label {
      font-size: .75rem;
      color: var(--muted);
      margin-top: .4rem;
    }

    /* ── Footer ── */
    footer {
      margin-top: 3.5rem;
      font-family: 'IBM Plex Mono', monospace;
      font-size: .7rem;
      color: var(--muted);
    }

    /* ── Responsive ── */
    @media (max-width: 460px) {
      .input-group { flex-direction: column; }
      .url-item { grid-template-columns: 1fr auto; }
      .original-url { grid-column: 1 / -1; }
      .stats-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<div class="wrapper">
  <header>
    <div class="nav">
      <span class="wordmark">shorten<span class="wordmark-dot">.</span></span>
      {% if request.endpoint == 'stats' %}
        <a class="nav-link" href="{{ url_for('index') }}">← home</a>
      {% else %}
        <a class="nav-link" href="{{ url_for('stats') }}">stats →</a>
      {% endif %}
    </div>
    <hr>
  </header>

  {% with messages = get_flashed_messages(with_categories=True) %}
    {% if messages %}
    <ul class="flashes">
      {% for cat, msg in messages %}
      <li class="{{ cat }}">{{ msg }}</li>
      {% endfor %}
    </ul>
    {% endif %}
  {% endwith %}

  {% block content %}{% endblock %}

  <footer>made by willyut</footer>
</div>

<script>
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('copy-btn')) {
      const url = e.target.dataset.url;
      navigator.clipboard.writeText(url).then(() => {
        const orig = e.target.textContent;
        e.target.textContent = '✓ copied';
        e.target.classList.add('copied');
        setTimeout(() => {
          e.target.textContent = orig;
          e.target.classList.remove('copied');
        }, 2000);
      });
    }
  });
</script>
</body>
</html>
"""

INDEX_TEMPLATE = HTML.replace(
    "{% block content %}{% endblock %}",
    """{% block content %}
  <form method="POST" action="{{ url_for('shorten') }}">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <div class="input-group">
      <input type="url" name="url" placeholder="https://example.com/very/long/url"
             required autocomplete="off" spellcheck="false"
             value="{{ prefill or '' }}">
      <button class="btn-primary" type="submit">Shorten</button>
    </div>
  </form>

  {% if recent %}
  <hr style="margin: 2rem 0;">
  <p class="section-label">Recent</p>
  <div class="url-list">
    {% for row in recent %}
    <div class="url-item">
      <a class="short-link" href="{{ base_url }}/{{ row['code'] }}" target="_blank">{{ base_url }}/{{ row['code'] }}</a>
      <span class="original-url" title="{{ row['original'] }}">{{ row['original'] }}</span>
      <button class="copy-btn" data-url="{{ base_url }}/{{ row['code'] }}">copy</button>
    </div>
    {% endfor %}
  </div>
  {% endif %}
{% endblock %}"""
)

STATS_TEMPLATE = HTML.replace(
    "{% block content %}{% endblock %}",
    """{% block content %}
  <p class="section-label">Statistics</p>
  <div class="stats-row">
    <div class="stat-box">
      <div class="num">{{ total }}</div>
      <div class="label">total urls</div>
    </div>
    <div class="stat-box">
      <div class="num">{{ last_hour }}</div>
      <div class="label">last hour</div>
    </div>
  </div>
{% endblock %}"""
)

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    recent = db.execute(
        "SELECT code, original FROM urls ORDER BY created DESC LIMIT 10"
    ).fetchall()
    base_url = request.host_url.rstrip('/')
    return render_template_string(
        INDEX_TEMPLATE,
        recent=recent,
        base_url=base_url,
        csrf_token=get_csrf_token(),
        prefill=None
    )

@app.route('/shorten', methods=['POST'])
@csrf_protect
def shorten():
    ip = request.remote_addr
    if is_rate_limited(ip):
        flash('Rate limit reached. Try again in a minute.', 'error')
        return redirect(url_for('index'))

    url = request.form.get('url', '').strip()
    if not url:
        flash('Please enter a URL.', 'error')
        return redirect(url_for('index'))

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not is_valid_url(url):
        flash('That doesn\'t look like a valid URL. Include http:// or https://.', 'error')
        return redirect(url_for('index'))

    url_hash = hashlib.sha256(url.encode()).hexdigest()
    db = get_db()

    existing = db.execute(
        "SELECT code FROM urls WHERE url_hash = ?", (url_hash,)
    ).fetchone()

    if existing:
        flash(f'Already shortened! Code: {existing["code"]}', 'info')
        return redirect(url_for('index'))

    # Generate unique code
    for _ in range(10):
        code = generate_code()
        conflict = db.execute("SELECT id FROM urls WHERE code = ?", (code,)).fetchone()
        if not conflict:
            break
    else:
        flash('Could not generate a unique code. Try again.', 'error')
        return redirect(url_for('index'))

    db.execute(
        "INSERT INTO urls (code, original, url_hash) VALUES (?, ?, ?)",
        (code, url, url_hash)
    )
    db.commit()

    flash(f'Shortened! Your code is: {code}', 'success')
    return redirect(url_for('index'))

@app.route('/<code>')
def redirect_url(code):
    if len(code) != 6 or not all(c in CHARS for c in code):
        flash('Invalid short code.', 'error')
        return redirect(url_for('index'))

    db = get_db()
    row = db.execute("SELECT original FROM urls WHERE code = ?", (code,)).fetchone()
    if not row:
        flash(f'Short code "{code}" not found.', 'error')
        return redirect(url_for('index'))

    db.execute("UPDATE urls SET hits = hits + 1 WHERE code = ?", (code,))
    db.commit()
    return redirect(row['original'])

@app.route('/stats')
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
    one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    last_hour = db.execute(
        "SELECT COUNT(*) FROM urls WHERE created >= ?", (one_hour_ago,)
    ).fetchone()[0]
    return render_template_string(
        STATS_TEMPLATE,
        total=total,
        last_hour=last_hour,
        csrf_token=get_csrf_token()
    )

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("  ✅  Database ready")
    print("  🌐  Running at: http://127.0.0.1:5000")
    print("  📊  Stats at:   http://127.0.0.1:5000/stats")
    print("  Made By Willyut\n")
    app.run(debug=False, port=5000)
