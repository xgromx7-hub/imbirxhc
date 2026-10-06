FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATA_DIR=/app/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -u 10001 -m bot && mkdir /app/data && chown bot:bot /app/data
COPY bot.py .
COPY imbirxhc ./imbirxhc
USER bot
STOPSIGNAL SIGTERM
CMD ["python", "-u", "bot.py"]
