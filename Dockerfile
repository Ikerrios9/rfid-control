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
    tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Madrid
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/log && chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]