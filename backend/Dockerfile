FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && useradd -u 10001 -m classroom && mkdir /data && chown classroom:classroom /data
COPY backend backend
USER classroom
ENV DATA_DIR=/data
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws-max-size", "1100000", "--ws-max-queue", "1"]
