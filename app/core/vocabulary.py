"""Controlled vocabulary for `region`/`industry` tags (CONTEXT.md: "Industry / Region Tag").

DB columns stay plain VARCHAR (see app/models/event.py) so adding a new tag never
requires an ALTER TYPE migration; membership is enforced at the Pydantic schema
boundary instead (see app/schemas/event.py). Extend these enums as new
industries/regions are onboarded during trial runs (spec §101/§102).
"""

from enum import StrEnum


class Industry(StrEnum):
    ZHUJIAN = "住建"
    FAGAI = "发改"
    JINGXIN = "经信"
    SHUJU = "数据"
    GUOZI = "国资"


class Region(StrEnum):
    CHONGQING = "重庆市"
