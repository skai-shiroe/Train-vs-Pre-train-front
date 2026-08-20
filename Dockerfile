# ============================================================================
# Dockerfile du frontend — application Streamlit Train-vs-Pre-train
#
# ⚠️ Le build context est la racine « Projet annuel » (voir docker-compose.yml)
#   pour rester cohérent avec le backend (context unique).
# ============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY Train-vs-Pre-train-front/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Sources de l'application Streamlit (seuls les fichiers nécessaires).
COPY Train-vs-Pre-train-front/streamlit_app.py .
COPY Train-vs-Pre-train-front/api_client.py .
COPY Train-vs-Pre-train-front/services.py .
COPY Train-vs-Pre-train-front/ui.py .
COPY Train-vs-Pre-train-front/monitoring.py .
COPY Train-vs-Pre-train-front/theme.py .
COPY Train-vs-Pre-train-front/examples.py .
COPY Train-vs-Pre-train-front/app_pages ./app_pages
COPY Train-vs-Pre-train-front/.streamlit ./.streamlit

# Dans le conteneur, l'URL de l'API est définie via la variable API_BASE_URL
# (voir docker-compose.yml -> http://backend:8000), lue par api_client.py.

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py"]