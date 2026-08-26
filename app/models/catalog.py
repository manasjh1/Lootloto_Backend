from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator
import re


def generate_slug(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")


# ── Categories ───────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category name cannot be empty")
        return v


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    uuid: str
    name: str
    slug: str
    is_active: bool
    created_at: str | datetime
    updated_at: str | datetime


# ── Product Images ───────────────────────────────────────

class ProductImageCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = 0
    is_primary: bool = False


class ProductImageResponse(BaseModel):
    uuid: str
    product_id: str
    url: str
    alt_text: str | None = None
    sort_order: int = 0
    is_primary: bool = False
    created_at: str | datetime


# ── Products ─────────────────────────────────────────────

ProductStatus = Literal["OK", "LOW_STOCK", "OUT_OF_STOCK", "DISCONTINUED"]


class ProductCreate(BaseModel):
    category_id: str
    sku: str = Field(..., min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=280)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    brand: str | None = Field(default=None, max_length=100)
    variant: str | None = Field(default=None, max_length=150)
    selling_price: float = Field(..., ge=0)
    compare_price: float | None = Field(default=None, ge=0)
    is_published: bool = False
    status: ProductStatus = "OK"

    # Admin / Inventory fields
    pack_qty: float | None = Field(default=None, ge=0)
    location_bin: str | None = Field(default=None, max_length=100)
    supplier: str | None = Field(default=None, max_length=150)
    purchase_date: date | str | None = None
    actual_unit_cost: float | None = Field(default=None, ge=0)
    opening_qty: int = Field(default=0, ge=0)
    current_qty: int = Field(default=0, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    notes: str | None = None

    # Initial images (optional)
    images: list[ProductImageCreate] = []

    @field_validator("sku", "name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or blank")
        return v


class ProductUpdate(BaseModel):
    category_id: str | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=280)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    brand: str | None = Field(default=None, max_length=100)
    variant: str | None = Field(default=None, max_length=150)
    selling_price: float | None = Field(default=None, ge=0)
    compare_price: float | None = Field(default=None, ge=0)
    is_published: bool | None = None
    status: ProductStatus | None = None

    pack_qty: float | None = Field(default=None, ge=0)
    location_bin: str | None = None
    supplier: str | None = None
    purchase_date: date | str | None = None
    actual_unit_cost: float | None = Field(default=None, ge=0)
    opening_qty: int | None = Field(default=None, ge=0)
    current_qty: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    notes: str | None = None


class ProductResponse(BaseModel):
    uuid: str
    category_id: str
    sku: str
    slug: str
    name: str
    description: str | None = None
    brand: str | None = None
    variant: str | None = None
    selling_price: float
    compare_price: float | None = None
    is_published: bool
    status: str

    # Admin / Inventory fields
    pack_qty: float | None = None
    location_bin: str | None = None
    supplier: str | None = None
    purchase_date: str | date | None = None
    actual_unit_cost: float | None = None
    opening_qty: int = 0
    current_qty: int = 0
    reorder_level: int | None = None
    notes: str | None = None

    # Audit & joins
    created_by: str | None = None
    updated_by: str | None = None
    created_at: str | datetime
    updated_at: str | datetime

    # Associated nested objects
    category: CategoryResponse | None = None
    images: list[ProductImageResponse] = []
