import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "agency.db"))

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production-please")
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]

# LLM providers (tried in order; first one with a key wins)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PAYMENT_LINK = os.environ.get("STRIPE_PAYMENT_LINK", "")  # legacy fallback
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Stripe Price IDs (create these in your Stripe dashboard -> Products)
STRIPE_PRICE_STARTER = os.environ.get("STRIPE_PRICE_STARTER", "")
STRIPE_PRICE_PRO = os.environ.get("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_AGENCY = os.environ.get("STRIPE_PRICE_AGENCY", "")

# Free tier: 3-day trial
FREE_TRIAL_DAYS = 3
FREE_POSTS_PER_WEEK = 5
FREE_BRANDS = 1

# Mobile money payment details (Uganda)
AIRTEL_NUMBER = os.environ.get("AIRTEL_NUMBER", "+256732474626")
MTN_NUMBER = os.environ.get("MTN_NUMBER", "+256769595165")
CURRENCY = "USD"

# Pricing plans (mobile money): 14 days $2, 1 month $5, 2 months $10
PLANS = {
    "free": {"name": "Free (3-day trial)", "price": 0, "days": FREE_TRIAL_DAYS, "posts": FREE_POSTS_PER_WEEK, "brands": FREE_BRANDS},
    "trial14": {"name": "14 Days", "price": 2, "days": 14, "posts": 30, "brands": 1},
    "monthly": {"name": "1 Month", "price": 5, "days": 30, "posts": 60, "brands": 1},
    "bimonthly": {"name": "2 Months", "price": 10, "days": 60, "posts": 120, "brands": 2},
}