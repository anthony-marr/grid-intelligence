with demand as (
    select
        ba,
        data_date,
        avg(demand_mw) as avg_demand_mw,
        max(demand_mw) as peak_demand_mw
    from {{ ref('stg_eia930_balance') }}
    group by 1, 2
),
weather as (
    select
        ts_utc::date as data_date,
        avg(temperature_c) as avg_temp_c,
        min(temperature_c) as min_temp_c,
        max(temperature_c) as max_temp_c
    from {{ ref('stg_weather_hourly') }}
    group by 1
)
select
    d.ba,
    d.data_date,
    d.avg_demand_mw,
    d.peak_demand_mw,
    w.avg_temp_c,
    w.min_temp_c,
    w.max_temp_c
from demand d
join weather w using (data_date)
