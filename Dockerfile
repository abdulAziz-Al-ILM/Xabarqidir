# Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY keywords.txt .  # If exists, otherwise it will be created

ENV TELEGRAM_TOKEN=your_token_here
ENV ADMIN_ID=your_admin_id_here

CMD ["python", "main.py"]
