select
    report_date,
    unit,
    -- "Beaver Valley 1" -> plant "Beaver Valley", unit_number 1
    regexp_extract(unit, '^(.*)\s+(\d+)$', 1) as plant,
    try_cast(regexp_extract(unit, '^(.*)\s+(\d+)$', 2) as integer) as unit_number,
    power_pct,
    coalesce(power_pct = 0, false) as at_zero_power,
    down_date,
    reason_or_comment,
    change_in_report,
    scrams
from read_parquet('{{ env_var("GRID_BRONZE_DIR", "data/bronze") }}/nrc_reactor_status/*.parquet')
