# Single image for both the FastAPI backend and the Streamlit UI.
# docker-compose runs it twice with different commands.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Heavy ML deps (FlagEmbedding/sentence-transformers) are optional at runtime;
# install the light set here and let demo_mode fall back if absent.
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

CMD ["uvicorn", "backend.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
