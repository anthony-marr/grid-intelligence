select
    report_date,
    plant,
    unit,
    unit_number,
    power_pct,
    at_zero_power,
    down_date,
    reason_or_comment,
    change_in_report,
    scrams
from {{ ref('stg_nrc_reactor_status') }}
