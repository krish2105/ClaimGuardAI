# Build context is the REPO ROOT (not backend/), so this image can also bake
# in the policies/ corpus, which lives as a sibling of backend/, not nested
# under it. See docker-compose.yml (`build.context: .`) and render.yaml
# (`dockerContext: .`) — both pass the repo root as context.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY policies /policies

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
