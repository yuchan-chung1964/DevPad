FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
# psycopg is the Postgres driver; the default SQLite database needs nothing extra.
RUN pip install --no-cache-dir -r requirements.txt "psycopg[binary]>=3.1"

COPY app ./app

RUN useradd --system --no-create-home appuser
USER appuser

# All configuration comes from environment variables (see README, "Deploying"). Nothing secret is baked in.
ENV PORT=8000 \
    ENABLE_DOCS=0
EXPOSE 8000

# One worker: the rate limiter keeps its counters in memory (see README). Set FORWARDED_ALLOW_IPS to your
# platform's proxy address so client IPs are read from X-Forwarded-For; the default trusts no one.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers"]
