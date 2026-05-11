# syntax=docker/dockerfile:1.6

# ----------- Build stage -----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ----------- Runtime stage -----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/app/.local/bin:$PATH

# Run as non-root for safety
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Copy installed packages from builder
COPY --from=builder --chown=app:app /root/.local /home/app/.local

# Copy application code
COPY --chown=app:app app/        ./app/
COPY --chown=app:app templates/  ./templates/
COPY --chown=app:app static/     ./static/
COPY --chown=app:app run.py      ./run.py

EXPOSE 5000

# Healthcheck for orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://localhost:5000/api/health', timeout=3).status == 200 else 1)"

CMD ["python", "run.py"]
