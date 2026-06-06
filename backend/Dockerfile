# Works for local Docker, docker-compose, and Hugging Face Spaces (sdk: docker).
FROM python:3.12-slim

# libgomp1 -> LightGBM; libglib2.0-0/libgl1 -> opencv (used by SHAP)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ libgomp1 libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# non-root user (Hugging Face Spaces runs as uid 1000)
RUN useradd -m -u 1000 user && chown -R user /app
USER user
ENV HOME=/home/user

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
