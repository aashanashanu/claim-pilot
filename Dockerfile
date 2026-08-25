FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e . && \
    rm -rf /root/.cache/pip

EXPOSE 8000

CMD ["uvicorn", "claimpilot.api:app", "--host", "0.0.0.0", "--port", "8000"]
