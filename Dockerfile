FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y wget curl unzip fonts-ipafont-gothic chromium chromium-driver && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
WORKDIR /app

ENV CHROME_PATH=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV DOWNLOAD_DIR=/app/pdf_output

CMD ["python", "main.py"]
