-- ============================================================
-- LootLooto · Migration 003 · RBAC Roles & Permissions Schema
-- Depends on: 001_auth_schema.sql, 002_catalog_schema.sql
-- ============================================================

-- 1. ROLES TABLE
CREATE TABLE IF NOT EXISTS roles (
    name        VARCHAR(30)     PRIMARY KEY, -- 'buyer', 'staff', 'admin'
    description TEXT            NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 2. PERMISSIONS TABLE
CREATE TABLE IF NOT EXISTS permissions (
    code        VARCHAR(50)     PRIMARY KEY, -- 'catalog:read', 'catalog:write', etc.
    name        VARCHAR(100)    NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 3. ROLE PERMISSIONS MAPPING TABLE
CREATE TABLE IF NOT EXISTS role_permissions (
    role_name       VARCHAR(30)  REFERENCES roles(name) ON DELETE CASCADE,
    permission_code VARCHAR(50)  REFERENCES permissions(code) ON DELETE CASCADE,
    PRIMARY KEY (role_name, permission_code)
);

-- 4. SEED ROLES
INSERT INTO roles (name, description) VALUES
    ('buyer', 'Standard customer who can browse products, manage cart, and place orders'),
    ('staff', 'Inventory and catalog management staff who can add, edit, and view products'),
    ('admin', 'Super Administrator with full access to manage catalog, staff accounts, and system settings')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;

-- 5. SEED PERMISSIONS
INSERT INTO permissions (code, name, description) VALUES
    ('catalog:read', 'View Catalog', 'Can view active categories and published products'),
    ('catalog:write', 'Manage Catalog', 'Can create, edit, and publish categories and products'),
    ('inventory:view_cost', 'View Inventory Cost', 'Can view purchase costs, supplier details, and margins'),
    ('users:create_staff', 'Create Staff', 'Can create and activate new staff accounts'),
    ('users:manage_all', 'Manage All Users', 'Can change roles, disable accounts, and manage all user data')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- 6. SEED ROLE PERMISSIONS
-- Buyer permissions
INSERT INTO role_permissions (role_name, permission_code) VALUES
    ('buyer', 'catalog:read')
ON CONFLICT DO NOTHING;

-- Staff permissions
INSERT INTO role_permissions (role_name, permission_code) VALUES
    ('staff', 'catalog:read'),
    ('staff', 'catalog:write')
ON CONFLICT DO NOTHING;

-- Admin permissions (Super Admin)
INSERT INTO role_permissions (role_name, permission_code) VALUES
    ('admin', 'catalog:read'),
    ('admin', 'catalog:write'),
    ('admin', 'inventory:view_cost'),
    ('admin', 'users:create_staff'),
    ('admin', 'users:manage_all')
ON CONFLICT DO NOTHING;

-- 7. SEED SUPER ADMIN USER
-- Email: admin@lootlooto.com | Password: AdminPassword123
INSERT INTO users (first_name, last_name, email_id, phone_number, password, role, is_verified, is_active)
VALUES (
    'Super',
    'Admin',
    'admin@lootlooto.com',
    9999999999,
    '$argon2id$v=19$m=65536,t=3,p=4$yog8+B61IRJAOYxnKS8few$tkRxOLsNc+wxPdrcSJMFpCOe7+nDMwgCVkkcYOeHPJw',
    'admin',
    TRUE,
    TRUE
)
ON CONFLICT (email_id) DO UPDATE SET
    role = 'admin',
    is_verified = TRUE,
    is_active = TRUE;

