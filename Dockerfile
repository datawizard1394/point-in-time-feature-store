FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
RUN useradd --create-home --uid 10001 featurestore
COPY --chown=featurestore:featurestore src ./src
COPY --chown=featurestore:featurestore data ./data
USER featurestore
ENTRYPOINT ["python", "-m", "feature_store"]
CMD ["demo", "--transactions", "data/transactions.csv", "--observations", "data/observations.csv", "--as-of", "2026-07-28T12:00:00Z", "--output-dir", "/tmp/feature-store"]
