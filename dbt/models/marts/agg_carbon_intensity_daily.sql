with hourly as (
    select
        f.ba,
        f.data_date,
        f.fuel,
        sum(f.mw) as mwh  -- hourly MW readings summed ~= MWh
    from {{ ref('fct_fuel_mix_hourly') }} f
    group by 1, 2, 3
)
select
    h.ba,
    h.data_date,
    sum(h.mwh) as total_mwh,
    sum(h.mwh * e.kg_co2_per_mwh) as emissions_kg,
    case when sum(h.mwh) > 0
         then sum(h.mwh * e.kg_co2_per_mwh) / sum(h.mwh)
    end as kg_co2_per_mwh,
    sum(case when h.fuel in ('nuclear', 'hydropower', 'solar', 'wind',
                             'geothermal')
             then h.mwh else 0 end)
        / nullif(sum(h.mwh), 0) as carbon_free_share
from hourly h
join {{ ref('emission_factors') }} e using (fuel)
group by 1, 2
