FROM python:3.11-slim

WORKDIR /app

COPY recall-server /app/recall-server

RUN pip install fastapi uvicorn websockets psutil

CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8000"]
