# Rasmiy Python asosiy tasviridan foydalanish
FROM python:3.11-slim

# Ishchi katalog o'rnatish
WORKDIR /usr/src/app

# Kodni nusxalashdan oldin keshni yangilash
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Kerakli paketlar
    && rm -rf /var/lib/apt/lists/*

# Talablar faylini nusxalash va bog'liqliklarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini nusxalash
COPY . .

# Botni ishga tushirish
CMD ["python", "main.py"]
