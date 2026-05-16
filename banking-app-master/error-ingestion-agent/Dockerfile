FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create log directory for db mode
RUN mkdir -p /var/log/banking-app

ENV MODE=db
ENV SERVICE_NAME=banking-app
ENV ENVIRONMENT=production

EXPOSE 8001

CMD ["python", "main.py"]
