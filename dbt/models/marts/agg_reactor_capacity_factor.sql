-- Unweighted mean of reported percent power over the loaded period: a
-- capacity-factor proxy (NRC reports percent of rated power, so a unit at
-- 100% every day averages 100). Days at 0% count as down.
select
    plant,
    unit,
    count(*) as days_reported,
    round(avg(power_pct), 2) as avg_power_pct,
    sum(case when at_zero_power then 1 else 0 end) as days_at_zero,
    max(report_date) as last_report_date
from {{ ref('fct_reactor_power_daily') }}
group by 1, 2
