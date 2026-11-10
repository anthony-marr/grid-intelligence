FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dbt/ ./dbt/
COPY src/ ./src/
# The built DuckDB (bronze Parquet + marts) is baked in by `fly deploy` from a
# local build: run grid-ingest + dbt build first so data/grid.duckdb exists.
COPY data/grid.duckdb ./data/grid.duckdb
ENV PYTHONPATH=/app/src \
    GRID_DUCKDB_PATH=/app/data/grid.duckdb
EXPOSE 8080
CMD ["uvicorn", "grid_intelligence.api:app", "--host", "0.0.0.0", "--port", "8080"]
