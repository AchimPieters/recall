FROM python:3.11-slim

WORKDIR /app

COPY recall-server /app/recall-server

RUN pip install --no-cache-dir fastapi uvicorn websockets psutil python-multipart

WORKDIR /app/recall-server/api
CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8000"]
