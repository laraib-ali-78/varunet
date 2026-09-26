FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    email-validator \
    numpy \
    pandas \
    scipy \
    scikit-learn \
    xgboost \
    shap \
    joblib \
    bcrypt \
    pyjwt \
    prometheus-fastapi-instrumentator \
    httpx \
    psycopg2-binary \
    sqlalchemy

# Copy application source
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
