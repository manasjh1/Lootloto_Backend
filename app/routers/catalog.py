from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.deps import get_current_user, require_staff_or_admin
from app.models.catalog import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ProductCreate,
    ProductImageCreate,
    ProductImageResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services import catalog_service

router = APIRouter()


# ── Categories ───────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(is_active_only: bool = False):
    """Retrieve list of categories."""
    return await catalog_service.list_categories(is_active_only=is_active_only)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    user=Depends(require_staff_or_admin)
):
    """Create a new product category (Staff / Admin only)."""
    try:
        category = await catalog_service.create_category(body)
        return category
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/categories/{uuid}", response_model=CategoryResponse)
async def update_category(
    uuid: str,
    body: CategoryUpdate,
    user=Depends(require_staff_or_admin)
):
    """Update existing category (Staff / Admin only)."""
    try:
        return await catalog_service.update_category(uuid, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Products ─────────────────────────────────────────────

@router.get("/products")
async def list_products(
    search: str | None = Query(default=None, description="Search by name, SKU, or brand"),
    category_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    is_published: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
):
    """List products with search, category/status filters, and page-based pagination."""
    return await catalog_service.list_products(
        search=search,
        category_id=category_id,
        status=status_filter,
        is_published=is_published,
        page=page,
        page_size=page_size,
        limit=limit,
        offset=offset,
    )



@router.get("/products/{uuid_or_slug}", response_model=ProductResponse)
async def get_product(uuid_or_slug: str):
    """Get single product details by UUID or slug."""
    product = await catalog_service.get_product_by_id(uuid_or_slug)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    user=Depends(require_staff_or_admin)
):
    """Create a new product in database (Staff / Admin only)."""
    try:
        product = await catalog_service.create_product(body, user_id=user["uuid"])
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/products/{uuid}", response_model=ProductResponse)
async def update_product(
    uuid: str,
    body: ProductUpdate,
    user=Depends(require_staff_or_admin)
):
    """Update product information (Staff / Admin only)."""
    try:
        product = await catalog_service.update_product(uuid, body, user_id=user["uuid"])
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/products/{uuid}", status_code=status.HTTP_200_OK)
async def delete_product(
    uuid: str,
    user=Depends(require_staff_or_admin)
):
    """Delete a product from the database (Staff / Admin only)."""
    deleted = await catalog_service.delete_product(uuid)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or delete failed")
    return {"message": "Product successfully deleted", "uuid": uuid}


# ── Product Images ───────────────────────────────────────

@router.post("/products/{uuid}/images", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
async def add_product_image(
    uuid: str,
    body: ProductImageCreate,
    user=Depends(require_staff_or_admin)
):
    """Add image to a product (Staff / Admin only)."""
    # Ensure product exists
    product = await catalog_service.get_product_by_id(uuid)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    try:
        image = await catalog_service.add_product_image(
            product_id=product["uuid"],
            url=body.url,
            alt_text=body.alt_text,
            sort_order=body.sort_order,
            is_primary=body.is_primary
        )
        return image
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/products/images/{image_id}")
async def delete_product_image(
    image_id: str,
    user=Depends(require_staff_or_admin)
):
    """Delete product image by ID (Staff / Admin only)."""
    success = await catalog_service.delete_product_image(image_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found or delete failed")
    return {"message": "Image deleted successfully", "image_id": image_id}


@router.put("/products/{uuid}/images/{image_id}/primary")
async def set_primary_image(
    uuid: str,
    image_id: str,
    user=Depends(require_staff_or_admin)
):
    """Set specified image as primary image for product (Staff / Admin only)."""
    try:
        return await catalog_service.set_primary_image(product_id=uuid, image_id=image_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


from fastapi import File, UploadFile

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    user=Depends(require_staff_or_admin)
):
    """Upload product image file directly to storage (Staff / Admin only)."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image (JPEG, PNG, WEBP, etc.)")

    file_bytes = await file.read()
    url = await catalog_service.upload_image_file(
        file_bytes=file_bytes,
        original_filename=file.filename or "image.jpg",
        content_type=file.content_type
    )
    return {"url": url, "filename": file.filename}

