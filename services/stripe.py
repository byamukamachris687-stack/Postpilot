"""Stripe Checkout + webhook helpers (no SDK, pure stdlib)."""
import hmac
import hashlib
import time
import urllib.request
import urllib.parse
import urllib.error
import json

from config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET


def _api_call(method, path, params=None):
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY not set")
    url = "https://api.stripe.com" + path
    data = None
    if params:
        data = urllib.parse.urlencode(params, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {STRIPE_SECRET_KEY}")
    if data:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Stripe API {method} {path} failed ({e.code}): {body}")


def create_checkout_session(user, price_id, plan, success_url, cancel_url):
    params = [
        ("mode", "subscription"),
        ("success_url", success_url),
        ("cancel_url", cancel_url),
        ("client_reference_id", str(user["id"])),
        ("customer_email", user["email"]),
        ("line_items[0][price]", price_id),
        ("line_items[0][quantity]", "1"),
        ("metadata[user_id]", str(user["id"])),
        ("metadata[plan]", plan),
        ("subscription_data[metadata][user_id]", str(user["id"])),
        ("subscription_data[metadata][plan]", plan),
    ]
    return _api_call("POST", "/v1/checkout/sessions", params)


def retrieve_session(session_id):
    return _api_call("GET", f"/v1/checkout/sessions/{session_id}")


def verify_webhook_signature(payload_bytes, sig_header, tolerance=300):
    """Return True if signature is valid."""
    if not STRIPE_WEBHOOK_SECRET or not sig_header:
        return False
    # parse "t=...,v1=..."
    parts = {}
    for item in sig_header.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            parts.setdefault(k, []).append(v)
    ts_list = parts.get("t")
    sig_list = parts.get("v1")
    if not ts_list or not sig_list:
        return False
    ts = ts_list[0]
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if abs(time.time() - ts_int) > tolerance:
        return False
    # Stripe signs: timestamp + "." + raw body
    signed = (ts + ".").encode() + payload_bytes
    expected = hmac.new(STRIPE_WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in sig_list)


def construct_event(payload_bytes):
    return json.loads(payload_bytes.decode("utf-8"))