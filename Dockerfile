FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ACEEST_DB=/data/aceest_fitness.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py test_app.py ./
COPY templates ./templates
COPY static ./static

RUN useradd --system --uid 1001 appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
