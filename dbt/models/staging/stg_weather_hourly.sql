select
    ts_utc,
    temperature_c
from read_parquet('{{ env_var("GRID_BRONZE_DIR", "data/bronze") }}/weather_hourly/*.parquet')
