FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY . /app
RUN chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --retries=5 --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/db', timeout=2)"

CMD ["python", "-m", "uvicorn", "apps.api_service.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
