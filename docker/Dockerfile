FROM python:3.11-slim

WORKDIR /app

COPY recall-server /app/recall-server
RUN pip install --no-cache-dir -r /app/recall-server/requirements.txt

WORKDIR /app/recall-server
CMD ["uvicorn","recall.api.main:app","--host","0.0.0.0","--port","8000"]
