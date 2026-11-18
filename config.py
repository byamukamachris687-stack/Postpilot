import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "agency.db")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production-please")

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

# Free tier limits
FREE_POSTS_PER_WEEK = 5
FREE_BRANDS = 1

# Pricing (display only; actual billing via Stripe)
PLANS = {
    "free": {"name": "Free", "price": 0, "posts": FREE_POSTS_PER_WEEK, "brands": FREE_BRANDS},
    "starter": {"name": "Starter", "price": 29, "posts": 30, "brands": 1},
    "pro": {"name": "Pro", "price": 79, "posts": 100, "brands": 5},
    "agency": {"name": "Agency", "price": 199, "posts": 500, "brands": 25},
}