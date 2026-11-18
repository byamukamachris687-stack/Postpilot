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
    plan_expires_at TEXT,
    stripe_customer_id TEXT,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    method TEXT NOT NULL,        -- airtel | mtn
    phone TEXT,                  -- sender phone
    txn_ref TEXT NOT NULL,       -- transaction reference / code
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    admin_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    verified_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
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
    # migrate: add is_admin column if missing
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "is_admin" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if "plan_expires_at" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN plan_expires_at TEXT")
    conn.commit()
    conn.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


# ---------- users ----------
def create_user(email, password_hash):
    import datetime
    # Free tier is a 3-day trial
    trial_expires = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, plan, plan_expires_at) VALUES (?,?,?,?)",
            (email.lower().strip(), password_hash, "free", trial_expires),
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


def ensure_plan_active(user):
    """Downgrade to free if the paid plan has expired. Admins never expire."""
    if not user:
        return user
    if user.get("is_admin"):
        return user
    if user.get("plan") == "free":
        # free trial: only block if expired (handled in posts_remaining/generate)
        return user
    expires = user.get("plan_expires_at")
    if not expires:
        return user
    import datetime
    try:
        if datetime.date.fromisoformat(expires) < datetime.date.today():
            update_user_plan(user["id"], "free")
            user["plan"] = "free"
            user["plan_expires_at"] = None
    except ValueError:
        pass
    return user


def update_user_plan(uid, plan, stripe_customer_id=None, plan_expires_at=None):
    conn = get_conn()
    if stripe_customer_id and plan_expires_at:
        conn.execute("UPDATE users SET plan=?, stripe_customer_id=?, plan_expires_at=? WHERE id=?", (plan, stripe_customer_id, plan_expires_at, uid))
    elif stripe_customer_id:
        conn.execute("UPDATE users SET plan=?, stripe_customer_id=? WHERE id=?", (plan, stripe_customer_id, uid))
    elif plan_expires_at is not None:
        conn.execute("UPDATE users SET plan=?, plan_expires_at=? WHERE id=?", (plan, plan_expires_at, uid))
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


# ---------- admin ----------
def get_all_users():
    conn = get_conn()
    rows = conn.execute(
        """SELECT u.*, (SELECT COUNT(*) FROM brands b WHERE b.user_id=u.id) AS brand_count,
                  (SELECT COUNT(*) FROM posts p WHERE p.user_id=u.id) AS post_count
           FROM users u ORDER BY u.created_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_users():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n


def count_posts():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    conn.close()
    return n


def count_brands_total():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    conn.close()
    return n


def set_user_admin(uid, is_admin):
    conn = get_conn()
    conn.execute("UPDATE users SET is_admin=? WHERE id=?", (1 if is_admin else 0, uid))
    conn.commit()
    conn.close()


def set_user_plan_admin(uid, plan):
    conn = get_conn()
    conn.execute("UPDATE users SET plan=? WHERE id=?", (plan, uid))
    conn.commit()
    conn.close()


def delete_user(uid):
    conn = get_conn()
    conn.execute("DELETE FROM usage WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM posts WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM brands WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()


def get_platform_stats():
    conn = get_conn()
    rows = conn.execute("SELECT platform, COUNT(*) AS n FROM posts GROUP BY platform").fetchall()
    conn.close()
    return {r["platform"]: r["n"] for r in rows}


# ---------- payments (mobile money) ----------
def create_payment(user_id, plan, amount, method, phone, txn_ref):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO payments (user_id, plan, amount, method, phone, txn_ref)
           VALUES (?,?,?,?,?,?)""",
        (user_id, plan, amount, method, phone, txn_ref),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def get_payments(status=None, limit=200):
    conn = get_conn()
    if status:
        rows = conn.execute(
            """SELECT p.*, u.email FROM payments p JOIN users u ON u.id=p.user_id
               WHERE p.status=? ORDER BY p.created_at DESC LIMIT ?""", (status, limit)).fetchall()
    else:
        rows = conn.execute(
            """SELECT p.*, u.email FROM payments p JOIN users u ON u.id=p.user_id
               ORDER BY p.created_at DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_payment(pid):
    conn = get_conn()
    row = conn.execute(
        """SELECT p.*, u.email FROM payments p JOIN users u ON u.id=p.user_id WHERE p.id=?""", (pid,)).fetchone()
    conn.close()
    return row_to_dict(row)


def approve_payment(pid, admin_uid, note=""):
    pay = get_payment(pid)
    if not pay or pay["status"] != "pending":
        return False
    import datetime
    plan = pay["plan"]
    from config import PLANS
    days = PLANS[plan]["days"]
    expires = (datetime.date.today() + datetime.timedelta(days=days)).isoformat() if days else None
    db_update = None
    conn = get_conn()
    conn.execute(
        "UPDATE payments SET status='approved', admin_note=?, verified_at=CURRENT_TIMESTAMP, verified_by=? WHERE id=?",
        (note, admin_uid, pid),
    )
    conn.commit()
    conn.close()
    update_user_plan(pay["user_id"], plan, plan_expires_at=expires)
    return True


def reject_payment(pid, admin_uid, note=""):
    conn = get_conn()
    conn.execute(
        "UPDATE payments SET status='rejected', admin_note=?, verified_at=CURRENT_TIMESTAMP, verified_by=? WHERE id=?",
        (note, admin_uid, pid),
    )
    conn.commit()
    conn.close()


def count_pending_payments():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    conn.close()
    return n