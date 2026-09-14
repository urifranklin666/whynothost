# WhyNotHost — platform image (backend + prebuilt frontend)
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY catalog /app/catalog
COPY frontend/dist/ui /app/frontend/dist/ui

ENV WNH_PORT=8022 \
    WNH_DATA_DIR=/data \
    PYTHONUNBUFFERED=1

VOLUME /data
EXPOSE 8022

HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8022/api/docs')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8022"]