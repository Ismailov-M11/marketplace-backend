# marketplace-backend

FastAPI + aiogram 3 backend for Marketplace Bot Platform.

## Setup

```bash
cp .env.example .env
# Edit .env with your values

pip install uv
uv pip install -e .

# Run migrations
alembic upgrade head

# Create first admin
python scripts/create_admin.py

# Start dev server
uvicorn app.main:app --reload
```

## Railway Deploy

1. Add PostgreSQL addon → Railway sets `DATABASE_URL` automatically
2. Add Redis addon → Railway sets `REDIS_URL` automatically
3. Set env vars from `.env.example` in Railway dashboard
4. Deploy — Dockerfile runs `alembic upgrade head` then `uvicorn`

## Environment Variables

See `.env.example` for all required variables.

Key ones for Railway:
- `DATABASE_URL` — auto-set by Railway PostgreSQL
- `REDIS_URL` — auto-set by Railway Redis
- `JWT_SECRET_KEY` — generate with `openssl rand -hex 32`
- `BOT_TOKEN_ENCRYPTION_KEY` — generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- `APP_ALLOWED_ORIGINS` — your frontend URLs

## API Docs

Available at `/docs` in development mode.

## Project Structure

```
app/
├── main.py          # FastAPI app entry point
├── settings.py      # Pydantic settings
├── core/            # Database, security, logging
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
├── api/
│   ├── public/      # Public endpoints (applications, health)
│   ├── admin/       # Super Admin API
│   ├── seller/      # Seller Admin API
│   └── miniapp/     # Telegram Mini App API
├── bots/            # aiogram handlers + dispatcher
├── utils/           # Helpers
alembic/             # DB migrations
scripts/             # CLI utilities
```
