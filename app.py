import os
import sys
import datetime

# make project root importable when run from anywhere
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file, g)
from werkzeug.security import generate_password_hash, check_password_hash

import config
from services import db
from services.ai import generate_posts, generate_ideas

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

db.init_db()

PRICE_IDS = {
    "starter": config.STRIPE_PRICE_STARTER,
    "pro": config.STRIPE_PRICE_PRO,
    "agency": config.STRIPE_PRICE_AGENCY,
}


# ---------- helpers ----------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.get_user_by_id(uid)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


def plan_limits(user):
    from config import PLANS
    return PLANS.get(user["plan"], PLANS["free"])


def posts_remaining(user):
    used = db.get_usage(user["id"])
    limit = plan_limits(user)["posts"]
    return max(0, limit - used)


@app.context_processor
def inject_globals():
    return {"user": current_user(), "plans": config.PLANS}


# ---------- public pages ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/sample", methods=["GET", "POST"])
def sample():
    """Free, no-login demo: prospect enters their business, gets 3 real posts instantly."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        industry = request.form.get("industry", "").strip()
        audience = request.form.get("audience", "").strip()
        tone = request.form.get("tone", "").strip()
        if not name:
            flash("Please enter a business name.", "warning")
            return render_template("sample.html")
        # light rate limit: 3 samples per session
        import time
        sess = session.setdefault("sample_runs", [])
        now = time.time()
        sess = [t for t in sess if now - t < 3600]
        if len(sess) >= 3:
            flash("You've used your 3 free samples this hour. Sign up for more, or contact us for a full week.", "warning")
            return render_template("sample.html")
        sess.append(now)
        session["sample_runs"] = sess

        brand = {
            "name": name,
            "industry": industry or "local business",
            "audience": audience or "local customers",
            "tone": tone or "friendly and professional",
            "products": "",
            "website": "",
        }
        platforms = ["instagram", "facebook", "tiktok"]
        posts = generate_posts(brand, platforms, 3)
        return render_template("sample.html", posts=posts, brand=brand, generated=True)
    return render_template("sample.html")


@app.route("/health")
def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}


# ---------- auth ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not email or not password or len(password) < 6:
            flash("Email and a password (6+ chars) are required.", "danger")
            return render_template("signup.html")
        if db.get_user_by_email(email):
            flash("An account with that email already exists.", "danger")
            return render_template("signup.html")
        uid = db.create_user(email, generate_password_hash(password))
        if uid is None:
            flash("Could not create account.", "danger")
            return render_template("signup.html")
        session["user_id"] = uid
        flash("Welcome! Let's set up your first brand.", "success")
        return redirect(url_for("onboarding"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        u = db.get_user_by_email(email)
        if u and check_password_hash(u["password_hash"], password):
            session["user_id"] = u["id"]
            nxt = request.args.get("next") or url_for("dashboard")
            return redirect(nxt)
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------- onboarding / brands ----------
@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    user = current_user()
    if request.method == "POST":
        data = {
            "name": request.form.get("name", "").strip(),
            "industry": request.form.get("industry", "").strip(),
            "audience": request.form.get("audience", "").strip(),
            "tone": request.form.get("tone", "").strip(),
            "platforms": ",".join(request.form.getlist("platforms")),
            "products": request.form.get("products", "").strip(),
            "website": request.form.get("website", "").strip(),
        }
        if not data["name"]:
            flash("Brand name is required.", "danger")
            return render_template("onboarding.html")
        # enforce brand limit
        if db.count_brands(user["id"]) >= plan_limits(user)["brands"]:
            flash("You've reached your brand limit. Upgrade to add more.", "warning")
            return redirect(url_for("pricing"))
        db.create_brand(user["id"], data)
        flash("Brand created! Generate your first batch of content.", "success")
        return redirect(url_for("dashboard"))
    return render_template("onboarding.html")


@app.route("/brands")
@login_required
def brands():
    user = current_user()
    return render_template("brands.html", brands=db.get_brands(user["id"]))


@app.route("/brands/<int:bid>/delete", methods=["POST"])
@login_required
def delete_brand(bid):
    user = current_user()
    db.delete_brand(bid, user["id"])
    flash("Brand deleted.", "info")
    return redirect(url_for("brands"))


# ---------- dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    bs = db.get_brands(user["id"])
    if not bs:
        return redirect(url_for("onboarding"))
    brand_id = request.args.get("brand_id", type=int) or bs[0]["id"]
    brand = db.get_brand(brand_id, user["id"]) or bs[0]
    posts = db.get_posts(user["id"], brand_id=brand["id"], limit=50)
    return render_template("dashboard.html", brands=bs, brand=brand, posts=posts,
                           remaining=posts_remaining(user), used=db.get_usage(user["id"]))


# ---------- generation ----------
@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    user = current_user()
    bs = db.get_brands(user["id"])
    if not bs:
        return redirect(url_for("onboarding"))
    if request.method == "POST":
        brand_id = int(request.form.get("brand_id"))
        brand = db.get_brand(brand_id, user["id"])
        if not brand:
            flash("Brand not found.", "danger")
            return redirect(url_for("dashboard"))
        platforms = request.form.getlist("platforms") or brand["platforms"].split(",")
        platforms = [p for p in platforms if p]
        if not platforms:
            flash("Select at least one platform.", "danger")
            return redirect(url_for("generate"))
        try:
            n = int(request.form.get("n_posts", 7))
        except ValueError:
            n = 7
        n = max(1, min(n, 30))
        # enforce free tier
        remaining = posts_remaining(user)
        if n > remaining:
            flash(f"You only have {remaining} posts left this week on the {user['plan']} plan. Upgrade for more.", "warning")
            if remaining <= 0:
                return redirect(url_for("pricing"))
            n = remaining
        extra = request.form.get("extra", "").strip()
        posts = generate_posts(brand, platforms, n, extra)
        db.save_posts(user["id"], brand["id"], posts)
        db.increment_usage(user["id"], len(posts))
        flash(f"Generated {len(posts)} posts!", "success")
        return redirect(url_for("dashboard", brand_id=brand["id"]))
    # GET
    brand_id = request.args.get("brand_id", type=int)
    brand = db.get_brand(brand_id, user["id"]) if brand_id else (bs[0] if bs else None)
    return render_template("generate.html", brands=bs, brand=brand, remaining=posts_remaining(user))


@app.route("/ideas", methods=["POST"])
@login_required
def ideas():
    user = current_user()
    brand_id = int(request.form.get("brand_id"))
    brand = db.get_brand(brand_id, user["id"])
    if not brand:
        return jsonify({"error": "brand not found"}), 404
    ideas_list = generate_ideas(brand, n=10)
    return jsonify({"ideas": ideas_list})


# ---------- posts management ----------
@app.route("/posts/<int:pid>/status", methods=["POST"])
@login_required
def post_status(pid):
    user = current_user()
    status = request.form.get("status", "draft")
    db.update_post_status(pid, user["id"], status)
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/posts/<int:pid>/delete", methods=["POST"])
@login_required
def post_delete(pid):
    user = current_user()
    db.delete_post(pid, user["id"])
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/export.csv")
@login_required
def export_csv():
    import csv, io
    user = current_user()
    brand_id = request.args.get("brand_id", type=int)
    posts = db.get_posts(user["id"], brand_id=brand_id, limit=1000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["platform", "content_type", "caption", "hashtags", "image_prompt", "best_time", "scheduled_date", "status"])
    for p in posts:
        w.writerow([p["platform"], p["content_type"], p["caption"], p["hashtags"],
                    p["image_prompt"], p["best_time"], p["scheduled_date"], p["status"]])
    from flask import Response
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=content-calendar.csv"})


# ---------- billing (Stripe) ----------
@app.route("/billing/checkout", methods=["POST"])
@login_required
def billing_checkout():
    plan = request.form.get("plan")
    if plan not in config.PLANS or plan == "free":
        flash("Invalid plan.", "danger")
        return redirect(url_for("pricing"))
    user = current_user()
    price_id = PRICE_IDS.get(plan, "")
    # Prefer real Stripe Checkout if configured
    if config.STRIPE_SECRET_KEY and price_id:
        try:
            from services.stripe import create_checkout_session
            base = request.url_root.rstrip("/")
            session = create_checkout_session(
                user, price_id, plan,
                success_url=base + "/billing/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=base + "/pricing",
            )
            return redirect(session["url"])
        except Exception as e:
            flash(f"Checkout error: {e}", "danger")
            return redirect(url_for("pricing"))
    # Fallback to legacy Payment Link
    link = config.STRIPE_PAYMENT_LINK
    if link:
        sep = "&" if "?" in link else "?"
        url = f"{link}{sep}client_reference_id={user['id']}&prefilled_email={user['email']}"
        return redirect(url)
    flash("Payments not configured yet. Set STRIPE_SECRET_KEY + STRIPE_PRICE_* (or STRIPE_PAYMENT_LINK) in env.", "warning")
    return redirect(url_for("pricing"))


@app.route("/billing/webhook", methods=["POST"])
def billing_webhook():
    from services.stripe import verify_webhook_signature, construct_event
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    if config.STRIPE_WEBHOOK_SECRET:
        if not verify_webhook_signature(payload, sig):
            return {"error": "invalid signature"}, 400
    try:
        event = construct_event(payload)
    except Exception:
        return {"error": "bad payload"}, 400

    etype = event.get("type", "")
    data = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed":
        uid = data.get("client_reference_id") or (data.get("metadata") or {}).get("user_id")
        plan = (data.get("metadata") or {}).get("plan")
        if uid and plan in config.PLANS:
            db.update_user_plan(int(uid), plan, stripe_customer_id=data.get("customer"))

    if etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        status = data.get("status")
        uid = (data.get("metadata") or {}).get("user_id")
        plan = (data.get("metadata") or {}).get("plan")
        if uid:
            if etype == "customer.subscription.deleted" or status in ("canceled", "unpaid"):
                db.update_user_plan(int(uid), "free")
            elif plan in config.PLANS:
                db.update_user_plan(int(uid), plan)

    return {"received": True}, 200


@app.route("/billing/success")
@login_required
def billing_success():
    session_id = request.args.get("session_id")
    if session_id and config.STRIPE_SECRET_KEY:
        try:
            from services.stripe import retrieve_session
            s = retrieve_session(session_id)
            plan = (s.get("metadata") or {}).get("plan")
            if plan in config.PLANS:
                db.update_user_plan(current_user()["id"], plan)
                flash(f"Welcome to {config.PLANS[plan]['name']}! Your plan is active.", "success")
        except Exception as e:
            flash(f"Could not verify session: {e}", "warning")
    else:
        flash("Payment received. Your plan will update shortly.", "success")
    return redirect(url_for("dashboard"))


@app.route("/account/upgrade", methods=["POST"])  # manual upgrade for demo
@login_required
def manual_upgrade():
    plan = request.form.get("plan")
    if plan in config.PLANS:
        db.update_user_plan(current_user()["id"], plan)
        flash(f"Upgraded to {config.PLANS[plan]['name']} (demo).", "success")
    return redirect(url_for("dashboard"))


@app.route("/settings")
@login_required
def settings():
    user = current_user()
    bs = db.get_brands(user["id"])
    return render_template("settings.html", brands=bs)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)