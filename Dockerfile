FROM python:3.9-slim

# Ishchi papkani belgilash
WORKDIR /app

# Kerakli fayllarni nusxalash
COPY requirements.txt .
COPY main.py .

# Kutubxonalarni o'rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Botni ishga tushirish
CMD ["python", "main.py"]
