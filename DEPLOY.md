# Deploy PostPilot (free) — step by step

## Option A: Render (easiest, free tier)

1. Push the `social-agency` folder to a GitHub repo.
2. Go to https://render.com → New → Web Service → connect the repo.
3. Render auto-detects `render.yaml`. Click "Apply".
4. In the dashboard, add env vars: `GROQ_API_KEY` (free from console.groq.com), and optionally `STRIPE_PAYMENT_LINK`.
5. Click "Create Web Service". First build ~2 min. You get a URL like `https://postpilot-xxxx.onrender.com`.
6. (Optional) Add a custom domain in Render → Settings → Custom Domains (e.g. postpilot.yourdomain.com).

Free tier sleeps after 15 min of inactivity (first request takes ~30s to wake). Fine for outreach; upgrade to $7/mo Starter for always-on once you have clients.

## Option B: Railway

1. Push to GitHub.
2. https://railway.app → New Project → Deploy from GitHub repo.
3. Add env vars in Variables tab.
4. Railway auto-detects Procfile. Deploy.

## Option C: Fly.io (always-on free allowance)

```bash
fly launch --no-deploy
fly secrets set GROQ_API_KEY=gsk_... SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
fly deploy
```

## Option D: $5 VPS (DigitalOcean/Hetzner) — best for production

```bash
# on the server
git clone <your-repo> && cd social-agency
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env   # fill keys
# run with systemd or pm2, behind nginx + certbot for HTTPS
gunicorn app:app --bind 0.0.0.0:8000 --workers 2
```

## After deploy — do these in order
1. Visit `https://your-url/sample` and generate 3 posts for a real restaurant. Screenshot them.
2. Set up a custom domain (looks 10x more credible in outreach).
3. Start the 7-day sprint in OUTREACH.md.

## Note on the database
SQLite file lives on the container's ephemeral disk on Render/Railway free tiers — data resets on redeploy. Fine for MVP. Once you have paying clients, move to Postgres (change `services/db.py` to use psycopg2; or use Render's free Postgres). Or just keep SQLite on a VPS with a persistent disk.