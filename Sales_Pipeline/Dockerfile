# ============================================================
#   Dockerfile — Sales ETL Pipeline (Python App)
#   Optional: use this to containerise the pipeline itself.
#   Default setup runs the pipeline on the host machine.
# ============================================================

FROM python:3.11-slim

LABEL maintainer="Sales ETL Pipeline"
LABEL description="Async ETL pipeline: Excel → PostgreSQL"

# ── System dependencies ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ──────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Copy project source ──────────────────────────────────────
COPY . .

# ── Create runtime directories ───────────────────────────────
RUN mkdir -p Input_Files Processed_Files Failed_Files Logs

# ── Environment (override via docker-compose or --env-file) ──
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/Code

CMD ["python", "Code/main.py"]