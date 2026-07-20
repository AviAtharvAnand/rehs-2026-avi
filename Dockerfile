FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY data/chunks/ ./data/chunks/
COPY chroma_db/ ./chroma_db/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

CMD ["streamlit", "run", "scripts/rag.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]