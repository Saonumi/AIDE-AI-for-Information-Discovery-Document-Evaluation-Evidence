"""CrawlItem — the contract every source crawler produces (FROZEN).

Maps cleanly onto the ingestion layer: doc_number/issued_date/effective_date become a
Document + its provisions; `relations` (AMENDS/SUPERSEDES/...) become ChangeEvents and
version chains. source crawlers fill what they can and leave the rest None.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    LUAT = "LUAT"
    PHAP_LENH = "PHAP_LENH"
    NGHI_DINH = "NGHI_DINH"
    NGHI_QUYET = "NGHI_QUYET"
    THONG_TU = "THONG_TU"
    QUYET_DINH = "QUYET_DINH"
    CONG_VAN = "CONG_VAN"
    VAN_BAN_HOP_NHAT = "VAN_BAN_HOP_NHAT"
    CHI_THI = "CHI_THI"
    THONG_BAO = "THONG_BAO"
    BIEU_PHI = "BIEU_PHI"           # SHB fee schedule
    LAI_SUAT = "LAI_SUAT"           # SHB interest-rate notice
    DIEU_KHOAN = "DIEU_KHOAN"       # product terms
    OTHER = "OTHER"


class RelationType(str, Enum):
    AMENDS = "AMENDS"                 # văn bản này sửa đổi văn bản khác
    AMENDED_BY = "AMENDED_BY"         # bị sửa đổi bởi
    SUPERSEDES = "SUPERSEDES"         # thay thế
    SUPERSEDED_BY = "SUPERSEDED_BY"   # bị thay thế bởi
    GUIDES = "GUIDES"                 # hướng dẫn
    GUIDED_BY = "GUIDED_BY"
    EXPIRES = "EXPIRES"               # làm hết hiệu lực
    RELATED = "RELATED"


class Relation(BaseModel):
    type: RelationType
    target_doc_number: Optional[str] = None
    target_title: Optional[str] = None
    target_url: Optional[str] = None


class CrawlItem(BaseModel):
    source: str                       # "vbpl" | "sbv" | "shb" | "thuvienphapluat"
    url: str
    doc_number: Optional[str] = None  # e.g. "39/2016/TT-NHNN"
    title: Optional[str] = None
    doc_type: Optional[DocType] = None
    issuer: Optional[str] = None      # cơ quan ban hành (NHNN, Chính phủ, ...)
    issued_date: Optional[date] = None
    effective_date: Optional[date] = None   # ngày có hiệu lực -> valid_from
    expiry_date: Optional[date] = None       # ngày hết hiệu lực (nếu biết)
    status: Optional[str] = None      # "Còn hiệu lực" / "Hết hiệu lực" / ...
    full_text: Optional[str] = None
    relations: List[Relation] = Field(default_factory=list)
    raw_path: Optional[str] = None    # local path of the saved raw html/pdf
    raw_sha256: Optional[str] = None  # sha256 of the exact raw bytes parsed (provenance)
    fetched_at: Optional[str] = None  # ISO timestamp
    is_banking: bool = False          # matched banking/finance keyword filter
    fields: dict = Field(default_factory=dict)   # source-specific extras
