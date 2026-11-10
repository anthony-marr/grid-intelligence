"""Pydantic models: every raw row validates here before it reaches bronze."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Eia930BalanceRow(BaseModel):
    """One hourly EIA-930 balance row for one balancing authority."""

    model_config = ConfigDict(str_strip_whitespace=True)

    balancing_authority: str = Field(min_length=1)
    data_date: dt.date
    hour_ending_utc: dt.datetime
    demand_mw: Optional[float] = None
    demand_forecast_mw: Optional[float] = None
    net_generation_mw: Optional[float] = None
    ng_coal_mw: Optional[float] = None
    ng_natural_gas_mw: Optional[float] = None
    ng_nuclear_mw: Optional[float] = None
    ng_petroleum_mw: Optional[float] = None
    ng_hydropower_mw: Optional[float] = None
    ng_pumped_storage_mw: Optional[float] = None
    ng_solar_mw: Optional[float] = None
    ng_wind_mw: Optional[float] = None
    ng_battery_storage_mw: Optional[float] = None
    ng_other_storage_mw: Optional[float] = None
    ng_geothermal_mw: Optional[float] = None
    ng_other_mw: Optional[float] = None
    ng_unknown_mw: Optional[float] = None

    @field_validator("balancing_authority")
    @classmethod
    def ba_upper(cls, v: str) -> str:
        return v.strip().upper()


class NrcReactorStatusRow(BaseModel):
    """One reactor's status line from a daily NRC Power Reactor Status Report."""

    model_config = ConfigDict(str_strip_whitespace=True)

    report_date: dt.date
    unit: str = Field(min_length=1)
    power_pct: Optional[float] = Field(default=None, ge=0, le=120)
    down_date: Optional[str] = None
    reason_or_comment: Optional[str] = None
    change_in_report: Optional[str] = None
    scrams: Optional[str] = None


class WeatherHourRow(BaseModel):
    """One hourly weather observation for the analysis location."""

    ts_utc: dt.datetime
    temperature_c: Optional[float] = None


class WeatherHourRow(BaseModel):
    """One hourly Open-Meteo archive row (UTC)."""

    ts_utc: dt.datetime
    temperature_c: float
