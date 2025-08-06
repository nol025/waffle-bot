# Dockerfile
FROM python:3.10-slim

# 1. set a working directory
WORKDIR /app

# 2. copy and install your deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. copy everything else
COPY . .

# 4. run your bot
CMD ["python", "woffle_bot_live.py"]




