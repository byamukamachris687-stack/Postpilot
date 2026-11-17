import sqlite3
import os
from config import DB_PATH, DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    audience TEXT,
    tone TEXT,
    platforms TEXT,            -- comma separated
    products TEXT,
    website TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    brand_id INTEGER NOT NULL,
    platform TEXT NOT NULL,    -- instagram|facebook|tiktok
    content_type TEXT,         -- reel|carousel|story|post|video
    caption TEXT NOT NULL,
    hashtags TEXT,
    image_prompt TEXT,
    best_time TEXT,
    scheduled_date TEXT,
    status TEXT DEFAULT 'draft', -- draft|approved|scheduled|posted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (brand_id) REFERENCES brands(id)
);

CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start TEXT NOT NULL,  -- YYYY-MM-DD (Monday)
    posts_generated INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, week_start)
);
"""


def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


# ---------- users ----------
def create_user(email, password_hash):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email.lower().strip(), password_hash),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    conn.close()
    return row_to_dict(row)


def get_user_by_id(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return row_to_dict(row)


def update_user_plan(uid, plan, stripe_customer_id=None):
    conn = get_conn()
    if stripe_customer_id:
        conn.execute("UPDATE users SET plan=?, stripe_customer_id=? WHERE id=?", (plan, stripe_customer_id, uid))
    else:
        conn.execute("UPDATE users SET plan=? WHERE id=?", (plan, uid))
    conn.commit()
    conn.close()


# ---------- brands ----------
def create_brand(user_id, data):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO brands (user_id, name, industry, audience, tone, platforms, products, website)
           VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, data["name"], data.get("industry"), data.get("audience"),
         data.get("tone"), data.get("platforms"), data.get("products"), data.get("website")),
    )
    conn.commit()
    bid = cur.lastrowid
    conn.close()
    return bid


def get_brands(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM brands WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_brand(brand_id, user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM brands WHERE id=? AND user_id=?", (brand_id, user_id)).fetchone()
    conn.close()
    return row_to_dict(row)


def count_brands(user_id):
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM brands WHERE user_id=?", (user_id,)).fetchone()[0]
    conn.close()
    return n


def delete_brand(brand_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM brands WHERE id=? AND user_id=?", (brand_id, user_id))
    conn.execute("DELETE FROM posts WHERE brand_id=? AND user_id=?", (brand_id, user_id))
    conn.commit()
    conn.close()


# ---------- posts ----------
def save_posts(user_id, brand_id, posts):
    conn = get_conn()
    ids = []
    for p in posts:
        cur = conn.execute(
            """INSERT INTO posts (user_id, brand_id, platform, content_type, caption, hashtags, image_prompt, best_time, scheduled_date)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, brand_id, p["platform"], p.get("content_type"), p["caption"],
             p.get("hashtags"), p.get("image_prompt"), p.get("best_time"), p.get("scheduled_date")),
        )
        ids.append(cur.lastrowid)
    conn.commit()
    conn.close()
    return ids


def get_posts(user_id, brand_id=None, platform=None, limit=200):
    conn = get_conn()
    q = "SELECT * FROM posts WHERE user_id=?"
    params = [user_id]
    if brand_id:
        q += " AND brand_id=?"; params.append(brand_id)
    if platform:
        q += " AND platform=?"; params.append(platform)
    q += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_post_status(post_id, user_id, status):
    conn = get_conn()
    conn.execute("UPDATE posts SET status=? WHERE id=? AND user_id=?", (status, post_id, user_id))
    conn.commit()
    conn.close()


def delete_post(post_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM posts WHERE id=? AND user_id=?", (post_id, user_id))
    conn.commit()
    conn.close()


# ---------- usage ----------
def _week_start():
    import datetime
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    return monday.isoformat()


def get_usage(user_id):
    ws = _week_start()
    conn = get_conn()
    row = conn.execute("SELECT posts_generated FROM usage WHERE user_id=? AND week_start=?", (user_id, ws)).fetchone()
    conn.close()
    return row["posts_generated"] if row else 0


def increment_usage(user_id, n):
    ws = _week_start()
    conn = get_conn()
    conn.execute(
        """INSERT INTO usage (user_id, week_start, posts_generated) VALUES (?,?,?)
           ON CONFLICT(user_id, week_start) DO UPDATE SET posts_generated = posts_generated + ?""",
        (user_id, ws, n, n),
    )
    conn.commit()
    conn.close()