import pytest
from app.models.catalog import CategoryCreate, ProductCreate, generate_slug
from app.core.security import create_access_token


def test_slug_generation():
    assert generate_slug("Table Matt Blue & Black!") == "table-matt-blue-black"
    assert generate_slug("   Special Product #123   ") == "special-product-123"


def test_category_create_validation():
    cat = CategoryCreate(name=" Table Cover ")
    assert cat.name == "Table Cover"
    assert cat.is_active is True

    with pytest.raises(ValueError):
        CategoryCreate(name="  ")


def test_product_create_validation():
    prod = ProductCreate(
        category_id="123e4567-e89b-12d3-a456-426614174000",
        sku="TB-MAT-BLU",
        name="Table Mat Blue",
        selling_price=299.50,
        status="OK",
    )
    assert prod.name == "Table Mat Blue"
    assert prod.sku == "TB-MAT-BLU"
    assert prod.selling_price == 299.50
    assert prod.status == "OK"
    assert prod.is_published is False
