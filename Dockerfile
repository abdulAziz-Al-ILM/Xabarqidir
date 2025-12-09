# Rasmiy Python asosiy rasmini ishlatish
FROM python:3.10-slim

# Ishchi katalog o'rnatish
WORKDIR /app

# Talab qilinadigan kutubxonalarni nusxalash va o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot kodini nusxalash
COPY main.py .

# Botni ishga tushirish
# BOT_TOKEN va ADMIN_ID muhit o'zgaruvchilari Railway'da o'rnatilishi kerak
CMD ["python", "main.py"]
