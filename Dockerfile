FROM python:3.11-slim

WORKDIR /app

# Dependencias para pyscard
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpcsclite1 \
    libpcsclite-dev \
    pcscd \
    pcsc-tools \
    swig \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/log && chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]