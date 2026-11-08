#1. Basis-Image: offizielles Python-Image mit version 3.0
FROM python:3.10-slim

#2. Arbeitsverzeichnis im Container festlegen
WORKDIR /app

#3. Abhängigkeit-Datei koperien und Paket installieren 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#4. den restlichen Projektcode Kopieren
COPY . .

#5.Den Port definieren, auf dem die App lauscht
EXPOSE 8000

#6. Den Befehel angeben, der beim START des containers ausgeführt wird
CMD ["uvicorn", "Main:app", "--host", "0.0.0.0", "--port", "8000"]
