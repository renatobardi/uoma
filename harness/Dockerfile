# Imagem oficial Playwright Python: já traz browsers + deps de sistema.
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: roda a exploração da Fase 2. Sobrescreva o command pra gerar specs (gen) etc.
CMD ["python", "-m", "uoma.explore"]
