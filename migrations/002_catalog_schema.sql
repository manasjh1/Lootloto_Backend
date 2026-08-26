-- ============================================================
-- LootLooto · Migration 002 · Catalog Schema
-- Depends on: 001_auth_schema.sql (users, set_updated_at())
-- ============================================================


-- ============================================================
-- USERS — extend role for product management
-- Your existing CHECK only allows ('buyer', 'admin'). Adding 'staff'
-- so you can have product editors without me giving them admin's other
-- powers (e.g. no cost/supplier visibility, enforced at app layer).
-- Skip this block if you don't need that distinction yet.
-- ============================================================
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check
    CHECK (role IN ('buyer', 'staff', 'admin'));

-- Ensure email_id on users is UNIQUE
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_id ON users (email_id);



-- ============================================================
-- CATEGORIES
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    uuid        UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100)    UNIQUE NOT NULL,       -- 'Table Matt'
    slug        VARCHAR(120)    UNIQUE NOT NULL,        -- for /category/:slug
    is_active   BOOLEAN         NOT NULL DEFAULT TRUE,

    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_categories_updated_at ON categories;
CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories (slug);


-- ============================================================
-- PRODUCTS
-- customer-facing fields + admin/inventory-only fields in one table.
-- Customer API selects only the safe columns.
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    uuid              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id       UUID            NOT NULL REFERENCES categories(uuid),

    -- customer-facing
    sku               VARCHAR(80)     UNIQUE NOT NULL,      -- 'TB MT BLUBLK'
    slug              VARCHAR(280)    UNIQUE NOT NULL,       -- for /products/:slug
    name              VARCHAR(255)    NOT NULL,
    description       TEXT,
    brand             VARCHAR(100),
    variant           VARCHAR(150),                          -- 'Blue Black 33x48'
    selling_price     NUMERIC(10,2)   NOT NULL,
    compare_price     NUMERIC(10,2),
    is_published      BOOLEAN         NOT NULL DEFAULT FALSE,
    status            VARCHAR(20)     NOT NULL DEFAULT 'OK'
                                      CHECK (status IN ('OK', 'LOW_STOCK', 'OUT_OF_STOCK', 'DISCONTINUED')),

    -- admin / inventory-only — never returned by customer API
    pack_qty          NUMERIC(10,2),
    location_bin      VARCHAR(100),
    supplier          VARCHAR(150),
    purchase_date     DATE,
    actual_unit_cost  NUMERIC(10,2),
    opening_qty       INTEGER         NOT NULL DEFAULT 0,
    current_qty       INTEGER         NOT NULL DEFAULT 0,
    reorder_level     INTEGER,
    notes             TEXT,

    -- audit
    created_by        UUID            REFERENCES users(uuid),
    updated_by        UUID            REFERENCES users(uuid),
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_products_category_id  ON products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_is_published ON products (is_published);
CREATE INDEX IF NOT EXISTS idx_products_status       ON products (status);
CREATE INDEX IF NOT EXISTS idx_products_slug         ON products (slug);


-- ============================================================
-- PRODUCT IMAGES (optional — 0 or more per product)
-- ============================================================
CREATE TABLE IF NOT EXISTS product_images (
    uuid        UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID            NOT NULL REFERENCES products(uuid) ON DELETE CASCADE,
    url         VARCHAR(500)    NOT NULL,
    alt_text    VARCHAR(255),
    sort_order  INTEGER         NOT NULL DEFAULT 0,
    is_primary  BOOLEAN         NOT NULL DEFAULT FALSE,

    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images (product_id);

-- Only one primary image per product
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_images_one_primary
    ON product_images (product_id)
    WHERE is_primary = TRUE;
