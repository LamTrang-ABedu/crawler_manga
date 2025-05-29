FROM python:3.10-slim

# --- Install Chrome & dependencies ---
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg2 fonts-liberation libnss3 libatk-bridge2.0-0 \
    libgtk-3-0 libxss1 libasound2 libx11-xcb1 libxcb-dri3-0 libgbm1 \
    libxcomposite1 libxdamage1 libxrandr2 libxshmfence1 libxinerama1 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Add Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && apt-get install -y google-chrome-stable

# Add ChromeDriver
ENV CHROMEDRIVER_VERSION=114.0.5735.90
RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip

# --- Python setup ---
WORKDIR /app
COPY . /app

# Avoid .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Port expose for Flask (default 5000)
EXPOSE 5000

# Entry point
CMD ["python", "app.py"]
