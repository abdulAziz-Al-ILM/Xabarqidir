# Asosiy Python 3.11 rasmini tanlash
FROM python:3.11-slim

# Ish katalogini o'rnatish
WORKDIR /app

# Dependency faylini nusxalash va kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Barcha bot kodlarini konteynerga nusxalash
COPY . .

# Bot ishlaydigan portni ochish (Telegram Webhook uchun)
# PORT environment variable orqali aniqlanadi, lekin Dockerfile'da ta'riflash yaxshi amaliyot
EXPOSE 8080

# Botni ishga tushirish buyrug'i
# Agar WEBHOOK_URL environment variable'i berilgan bo'lsa, main.py uni ishlatadi.
CMD ["python", "main.py"]
