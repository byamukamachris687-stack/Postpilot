# PostPilot — AI Social Media Agency

A complete, runnable SaaS starter that helps businesses create Facebook, Instagram and TikTok content.
Built to be the engine behind an "AI social media agency" — either sold as a self-serve tool ($29–$199/mo)
or used by you to run clients' accounts ($200–$500/mo each).

## Why this can earn $50/day

- $50/day ≈ $1,500/mo. At $29/mo you need ~52 paying customers (or 8–15 agency clients).
- Free tier (5 posts/week) drives signups and SEO; paid plans $2/$5/$10 via Airtel Money or MTN MoMo.
- B2B buyers churn less and pay more than consumers.
- Fastest cash: offer a "done-for-you" service using this tool to local businesses while the SaaS ramps.

## Quick start (local)

```bash
cd social-agency
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit as needed
python app.py
```

Open http://localhost:5000

Works WITHOUT an OpenAI key — demo mode generates placeholder content so you can test the whole flow.

## Going to production

1. Set a strong `SECRET_KEY` and `GROQ_API_KEY` (free) or `OPENAI_API_KEY`.
2. Stripe setup (full Checkout, not just payment links):
   - Create a Stripe account → Dashboard → Products → add 3 products (Starter $29, Pro $79, Agency $199) with monthly recurring prices.
   - Copy each Price ID (`price_...`) into `STRIPE_PRICE_STARTER/PRO/AGENCY`.
   - Developers → API keys → copy the Secret key into `STRIPE_SECRET_KEY`.
   - Developers → Webhooks → add endpoint `https://yourdomain.com/billing/webhook`, subscribe to `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`. Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
3. Deploy to Render / Railway / Fly.io (free tier works for MVP) or a $5 VPS.
4. Point a custom domain at it.
5. Test a real checkout with Stripe's test card `4242 4242 4242 4242`.

## Earning plan (90 days)

- **Week 1–2:** Deploy, post in 3 niche communities (e.g. r/smallbusiness, local FB groups, LinkedIn).
  Offer 5 free audits → convert 1–2 to $200/mo managed clients.
- **Week 3–6:** Publish 4 SEO articles ("free Instagram caption generator", "TikTok hook ideas", etc.).
  Each ranks → steady free signups.
- **Week 7–12:** Add testimonials, raise prices, upsell Agency tier. Target: 50 paid users OR 10 managed clients.

## Project layout

```
app.py            Flask app + routes
config.py         env + plans
services/db.py    SQLite (users, brands, posts, usage)
services/ai.py    OpenAI wrapper + demo mock
services/prompts.py
templates/        Jinja2 views
static/           CSS/JS
```

## License

MIT — do whatever you want.