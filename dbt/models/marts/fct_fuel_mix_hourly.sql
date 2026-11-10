with unpivoted as (
    unpivot {{ ref('stg_eia930_balance') }}
    on ng_coal_mw, ng_natural_gas_mw, ng_nuclear_mw, ng_petroleum_mw,
       ng_hydropower_mw, ng_pumped_storage_mw, ng_solar_mw, ng_wind_mw,
       ng_battery_storage_mw, ng_geothermal_mw, ng_other_mw, ng_unknown_mw
    into
        name fuel_col
        value mw
)
select
    ba,
    hour_ending_utc,
    data_date,
    demand_mw,
    net_generation_mw,
    replace(replace(fuel_col, 'ng_', ''), '_mw', '') as fuel,
    mw
from unpivoted
