from postgrest.exceptions import APIError
from app.core.config import settings
from app.models.catalog import CategoryCreate, CategoryUpdate, ProductCreate, ProductUpdate, generate_slug
from app.services.db import get_db


# ── Categories Service ────────────────────────────────────

async def create_category(data: CategoryCreate) -> dict:
    db = get_db()
    slug = data.slug.strip() if data.slug else generate_slug(data.name)
    payload = {
        "name": data.name,
        "slug": slug,
        "is_active": data.is_active,
    }
    try:
        res = db.table("categories").insert(payload).execute()
        return res.data[0]
    except APIError as e:
        raise ValueError(f"Category creation failed: {e.message}")


async def list_categories(is_active_only: bool = False) -> list[dict]:
    db = get_db()
    query = db.table("categories").select("*").order("name")
    if is_active_only:
        query = query.eq("is_active", True)
    res = query.execute()
    return res.data or []


async def get_category_by_id(category_id: str) -> dict | None:
    db = get_db()
    try:
        res = db.table("categories").select("*").eq("uuid", category_id).single().execute()
        return res.data
    except Exception:
        return None


async def update_category(category_id: str, data: CategoryUpdate) -> dict:
    db = get_db()
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "name" in update_data and "slug" not in update_data:
        update_data["slug"] = generate_slug(update_data["name"])
    
    if not update_data:
        existing = await get_category_by_id(category_id)
        if not existing:
            raise ValueError("Category not found")
        return existing

    try:
        res = db.table("categories").update(update_data).eq("uuid", category_id).execute()
        if not res.data:
            raise ValueError("Category not found")
        return res.data[0]
    except APIError as e:
        raise ValueError(f"Category update failed: {e.message}")


# ── Products Service ──────────────────────────────────────

async def create_product(data: ProductCreate, user_id: str) -> dict:
    db = get_db()

    # Generate slug if omitted
    slug = data.slug.strip() if data.slug else generate_slug(data.name)
    
    # Check if slug exists, append SKU or timestamp if collision
    existing_slug = db.table("products").select("uuid").eq("slug", slug).execute()
    if existing_slug.data:
        slug = f"{slug}-{generate_slug(data.sku)}"

    # Convert model to dict, exclude images
    product_dict = data.model_dump(exclude={"images"})
    product_dict["slug"] = slug
    product_dict["created_by"] = user_id
    product_dict["updated_by"] = user_id

    # Format date field to string if date object
    if product_dict.get("purchase_date"):
        product_dict["purchase_date"] = str(product_dict["purchase_date"])

    try:
        # 1. Insert product
        res = db.table("products").insert(product_dict).execute()
        product_row = res.data[0]
        product_id = product_row["uuid"]

        # 2. Insert initial images if provided
        if data.images:
            has_primary = False
            img_payloads = []
            for idx, img in enumerate(data.images):
                is_prim = img.is_primary
                if is_prim and has_primary:
                    is_prim = False
                elif is_prim:
                    has_primary = True

                # If no image is explicitly set primary, set first one as primary
                if idx == 0 and not has_primary and len(data.images) > 0:
                    is_prim = True
                    has_primary = True

                img_payloads.append({
                    "product_id": product_id,
                    "url": img.url,
                    "alt_text": img.alt_text,
                    "sort_order": img.sort_order if img.sort_order != 0 else idx,
                    "is_primary": is_prim
                })
            
            if img_payloads:
                db.table("product_images").insert(img_payloads).execute()

        # Return product with categories and product_images
        return await get_product_by_id(product_id)

    except APIError as e:
        raise ValueError(f"Product creation failed: {e.message}")


async def list_products(
    search: str | None = None,
    category_id: str | None = None,
    status: str | None = None,
    is_published: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    limit: int | None = None,
    offset: int | None = None
) -> dict:
    db = get_db()
    
    # Calculate offset and limit if page & page_size are provided
    if limit is None:
        limit = page_size
    if offset is None:
        offset = (page - 1) * limit

    # Query with category and product_images joins
    query = db.table("products").select(
        "*, category:categories(*), images:product_images(*)", count="exact"
    )

    if category_id:
        query = query.eq("category_id", category_id)
    if status:
        query = query.eq("status", status)
    if is_published is not None:
        query = query.eq("is_published", is_published)
    if search:
        s = f"%{search.strip()}%"
        query = query.or_(f"name.ilike.{s},sku.ilike.{s},brand.ilike.{s}")

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    res = query.execute()

    items = res.data or []
    # Sort images inside each product by sort_order & is_primary
    for item in items:
        if "images" in item and item["images"]:
            item["images"] = sorted(item["images"], key=lambda x: (not x.get("is_primary", False), x.get("sort_order", 0)))

    total_count = res.count if res.count is not None else len(items)
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
    current_page = (offset // limit) + 1 if limit > 0 else 1

    return {
        "items": items,
        "total": total_count,
        "page": current_page,
        "page_size": limit,
        "total_pages": total_pages,
        "has_next": current_page < total_pages,
        "has_prev": current_page > 1
    }



async def get_product_by_id(product_id: str) -> dict | None:
    db = get_db()
    try:
        # Check by uuid first
        res = db.table("products").select(
            "*, category:categories(*), images:product_images(*)"
        ).eq("uuid", product_id).execute()

        if not res.data:
            # Try matching slug
            res = db.table("products").select(
                "*, category:categories(*), images:product_images(*)"
            ).eq("slug", product_id).execute()

        if not res.data:
            return None

        product = res.data[0]
        if "images" in product and product["images"]:
            product["images"] = sorted(product["images"], key=lambda x: (not x.get("is_primary", False), x.get("sort_order", 0)))
        return product
    except Exception as e:
        print(f"[get_product_by_id error] {e}")
        return None


async def update_product(product_id: str, data: ProductUpdate, user_id: str) -> dict:
    db = get_db()
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    
    if "name" in update_data and "slug" not in update_data:
        update_data["slug"] = generate_slug(update_data["name"])

    if "purchase_date" in update_data and update_data["purchase_date"]:
        update_data["purchase_date"] = str(update_data["purchase_date"])

    update_data["updated_by"] = user_id

    try:
        res = db.table("products").update(update_data).eq("uuid", product_id).execute()
        if not res.data:
            raise ValueError("Product not found")
        return await get_product_by_id(product_id)
    except APIError as e:
        raise ValueError(f"Product update failed: {e.message}")


async def delete_product(product_id: str) -> bool:
    db = get_db()
    try:
        res = db.table("products").delete().eq("uuid", product_id).execute()
        return bool(res.data)
    except Exception:
        return False


# ── Product Images Service ────────────────────────────────

async def add_product_image(
    product_id: str,
    url: str,
    alt_text: str | None = None,
    sort_order: int = 0,
    is_primary: bool = False
) -> dict:
    db = get_db()

    # If setting primary, reset existing primary images for this product first
    if is_primary:
        db.table("product_images").update({"is_primary": False}).eq("product_id", product_id).execute()

    # If first image for this product, default to primary
    existing_imgs = db.table("product_images").select("uuid").eq("product_id", product_id).execute()
    if not existing_imgs.data:
        is_primary = True

    try:
        res = db.table("product_images").insert({
            "product_id": product_id,
            "url": url,
            "alt_text": alt_text,
            "sort_order": sort_order,
            "is_primary": is_primary
        }).execute()
        return res.data[0]
    except APIError as e:
        raise ValueError(f"Adding product image failed: {e.message}")


async def delete_product_image(image_id: str) -> bool:
    db = get_db()
    try:
        res = db.table("product_images").delete().eq("uuid", image_id).execute()
        return bool(res.data)
    except Exception:
        return False


async def set_primary_image(product_id: str, image_id: str) -> dict:
    db = get_db()
    # 1. Unset primary flag on all images for product
    db.table("product_images").update({"is_primary": False}).eq("product_id", product_id).execute()
    # 2. Set primary flag on selected image
    res = db.table("product_images").update({"is_primary": True}).eq("uuid", image_id).execute()
    if not res.data:
        raise ValueError("Image not found")
    return res.data[0]


import os
import uuid

async def upload_image_file(file_bytes: bytes, original_filename: str, content_type: str) -> str:
    """Uploads image file to Supabase Storage bucket 'product-images', or fallback to local static folder."""
    db = get_db()
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4()}{ext}"
    
    # 1. Try Supabase Storage upload
    try:
        bucket_name = "product-images"
        db.storage.from_(bucket_name).upload(
            path=unique_name,
            file=file_bytes,
            file_options={"content-type": content_type or "image/jpeg"}
        )
        return db.storage.from_(bucket_name).get_public_url(unique_name)
    except Exception as e:
        print(f"[Supabase Storage Upload Warning] {e}. Falling back to local static storage.")

    # 2. Fallback to local static uploads directory
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return f"/static/uploads/{unique_name}"

