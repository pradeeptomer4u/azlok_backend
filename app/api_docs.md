# Inventory Management System API Documentation

This document provides details on all the APIs available in the Inventory Management System, along with curl examples for each endpoint.

## Authentication

All API endpoints require authentication using a JWT token. The token should be included in the Authorization header as a Bearer token.

```bash
curl -X GET "http://localhost:8000/api/inventory/items" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Table of Contents

1. [Raw Material Management](#raw-material-management)
2. [Packaged Products](#packaged-products)
3. [Purchase Management](#purchase-management)
4. [Production Management](#production-management)
5. [Gate Pass System](#gate-pass-system)

## Raw Material Management

### Create Inventory Item

**Endpoint:** `POST /api/inventory/items`

**Description:** Create a new inventory item (raw material or finished good).

**Request Body:**
```json
{
  "name": "Sugar",
  "code": "RM001",
  "description": "White refined sugar",
  "category_id": 1,
  "unit_of_measure": "kilogram",
  "min_stock_level": 10,
  "max_stock_level": 100,
  "reorder_level": 20,
  "cost_price": 45.5,
  "hsn_code": "1701",
  "is_active": true,
  "is_raw_material": true
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/inventory/items" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sugar",
    "code": "RM001",
    "description": "White refined sugar",
    "category_id": 1,
    "unit_of_measure": "kilogram",
    "min_stock_level": 10,
    "max_stock_level": 100,
    "reorder_level": 20,
    "cost_price": 45.5,
    "hsn_code": "1701",
    "is_active": true,
    "is_raw_material": true
  }'
```

### Get All Inventory Items

**Endpoint:** `GET /api/inventory/items`

**Description:** Get a list of all inventory items.

**Query Parameters:**
- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Maximum number of items to return (default: 100)
- `search` (optional): Search term for name, code, or description
- `category_id` (optional): Filter by category ID
- `is_raw_material` (optional): Filter by raw material status (true/false)
- `is_active` (optional): Filter by active status (true/false)
- `sort_by` (optional): Field to sort by (name, code, current_stock, created_at)
- `sort_order` (optional): Sort order (asc, desc)

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/inventory/items?limit=10&is_raw_material=true&sort_by=name" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Inventory Item by ID

**Endpoint:** `GET /api/inventory/items/{item_id}`

**Description:** Get details of a specific inventory item.

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/inventory/items/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Inventory Item

**Endpoint:** `PUT /api/inventory/items/{item_id}`

**Description:** Update an existing inventory item.

**Request Body:**
```json
{
  "name": "Refined Sugar",
  "description": "Premium white refined sugar",
  "min_stock_level": 15,
  "reorder_level": 25
}
```

**Curl Example:**
```bash
curl -X PUT "http://localhost:8000/api/inventory/items/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Refined Sugar",
    "description": "Premium white refined sugar",
    "min_stock_level": 15,
    "reorder_level": 25
  }'
```

### Delete Inventory Item

**Endpoint:** `DELETE /api/inventory/items/{item_id}`

**Description:** Delete an inventory item. If the item has stock movements, it will be marked as inactive instead of being deleted.

**Curl Example:**
```bash
curl -X DELETE "http://localhost:8000/api/inventory/items/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Inventory Stock Status

**Endpoint:** `GET /api/inventory/items/stock-status`

**Description:** Get the stock status of all inventory items, including whether they are below reorder level or minimum stock level.

**Query Parameters:**
- `is_raw_material` (optional): Filter by raw material status (true/false)
- `category_id` (optional): Filter by category ID

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/inventory/items/stock-status?is_raw_material=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Stock Movement

**Endpoint:** `POST /api/inventory/stock-movements`

**Description:** Create a new stock movement (purchase, production, sales, etc.).

**Request Body:**
```json
{
  "inventory_item_id": 1,
  "movement_type": "purchase",
  "quantity": 50,
  "unit_price": 45.5,
  "reference_number": "PO00001",
  "reference_type": "purchase_order",
  "reference_id": 1,
  "notes": "Initial stock purchase"
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/inventory/stock-movements" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inventory_item_id": 1,
    "movement_type": "purchase",
    "quantity": 50,
    "unit_price": 45.5,
    "reference_number": "PO00001",
    "reference_type": "purchase_order",
    "reference_id": 1,
    "notes": "Initial stock purchase"
  }'
```

### Get Stock Movements

**Endpoint:** `GET /api/inventory/stock-movements`

**Description:** Get a list of stock movements.

**Query Parameters:**
- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Maximum number of items to return (default: 100)
- `inventory_item_id` (optional): Filter by inventory item ID
- `movement_type` (optional): Filter by movement type
- `reference_type` (optional): Filter by reference type
- `reference_id` (optional): Filter by reference ID
- `start_date` (optional): Filter by start date
- `end_date` (optional): Filter by end date

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/inventory/stock-movements?inventory_item_id=1&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Packaged Products

### Create Packaged Product

**Endpoint:** `POST /api/packaged-products`

**Description:** Create a new packaged product.

**Request Body:**
```json
{
  "product_id": 1,
  "packaging_size": "SIZE_100G",
  "weight_value": 100,
  "weight_unit": "g",
  "items_per_package": 1,
  "barcode": "8901234567890",
  "min_stock_level": 10,
  "reorder_level": 20,
  "is_active": true
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/packaged-products" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "packaging_size": "SIZE_100G",
    "weight_value": 100,
    "weight_unit": "g",
    "items_per_package": 1,
    "barcode": "8901234567890",
    "min_stock_level": 10,
    "reorder_level": 20,
    "is_active": true
  }'
```

### Get All Packaged Products

**Endpoint:** `GET /api/packaged-products`

**Description:** Get a list of all packaged products.

**Query Parameters:**
- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Maximum number of items to return (default: 100)
- `product_id` (optional): Filter by product ID
- `packaging_size` (optional): Filter by packaging size
- `is_active` (optional): Filter by active status (true/false)

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/packaged-products?product_id=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Packaged Product by ID

**Endpoint:** `GET /api/packaged-products/{packaged_product_id}`

**Description:** Get details of a specific packaged product.

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/packaged-products/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Packaged Product

**Endpoint:** `PUT /api/packaged-products/{packaged_product_id}`

**Description:** Update an existing packaged product.

**Request Body:**
```json
{
  "barcode": "8901234567891",
  "min_stock_level": 15,
  "reorder_level": 25
}
```

**Curl Example:**
```bash
curl -X PUT "http://localhost:8000/api/packaged-products/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "barcode": "8901234567891",
    "min_stock_level": 15,
    "reorder_level": 25
  }'
```

### Delete Packaged Product

**Endpoint:** `DELETE /api/packaged-products/{packaged_product_id}`

**Description:** Delete a packaged product. If the product has movements, it will be marked as inactive instead of being deleted.

**Curl Example:**
```bash
curl -X DELETE "http://localhost:8000/api/packaged-products/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Packaged Product Movement

**Endpoint:** `POST /api/packaged-products/movements`

**Description:** Create a new packaged product movement.

**Request Body:**
```json
{
  "packaged_product_id": 1,
  "movement_type": "production",
  "quantity": 100,
  "reference_number": "BATCH00001",
  "reference_type": "production_batch",
  "reference_id": 1,
  "notes": "Production batch completion"
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/packaged-products/movements" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "packaged_product_id": 1,
    "movement_type": "production",
    "quantity": 100,
    "reference_number": "BATCH00001",
    "reference_type": "production_batch",
    "reference_id": 1,
    "notes": "Production batch completion"
  }'
```

### Get Packaged Product Stock Status

**Endpoint:** `GET /api/packaged-products/stock-status`

**Description:** Get the stock status of all packaged products.

**Query Parameters:**
- `product_id` (optional): Filter by product ID
- `packaging_size` (optional): Filter by packaging size
- `is_active` (optional): Filter by active status (true/false)

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/packaged-products/stock-status?product_id=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Purchase Management

### Create Supplier

**Endpoint:** `POST /api/purchase/suppliers`

**Description:** Create a new supplier.

**Request Body:**
```json
{
  "name": "ABC Suppliers",
  "code": "SUP001",
  "contact_person": "John Doe",
  "email": "john@abcsuppliers.com",
  "phone": "9876543210",
  "address": "123 Main St, City",
  "gst_number": "29ABCDE1234F1Z5",
  "pan_number": "ABCDE1234F",
  "payment_terms": "Net 30",
  "credit_limit": 100000,
  "is_active": true,
  "notes": "Preferred supplier for sugar"
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/purchase/suppliers" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ABC Suppliers",
    "code": "SUP001",
    "contact_person": "John Doe",
    "email": "john@abcsuppliers.com",
    "phone": "9876543210",
    "address": "123 Main St, City",
    "gst_number": "29ABCDE1234F1Z5",
    "pan_number": "ABCDE1234F",
    "payment_terms": "Net 30",
    "credit_limit": 100000,
    "is_active": true,
    "notes": "Preferred supplier for sugar"
  }'
```

### Create Purchase Indent

**Endpoint:** `POST /api/purchase/indents`

**Description:** Create a new purchase indent (request for purchase).

**Request Body:**
```json
{
  "department": "Production",
  "request_date": "2025-10-15",
  "required_by_date": "2025-10-20",
  "status": "pending",
  "notes": "Urgent requirement for production",
  "items": [
    {
      "inventory_item_id": 1,
      "quantity": 50,
      "unit_of_measure": "kilogram",
      "estimated_price": 45.5,
      "notes": "Premium quality required"
    },
    {
      "inventory_item_id": 2,
      "quantity": 20,
      "unit_of_measure": "kilogram",
      "estimated_price": 60.0,
      "notes": ""
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/purchase/indents" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "Production",
    "request_date": "2025-10-15",
    "required_by_date": "2025-10-20",
    "status": "pending",
    "notes": "Urgent requirement for production",
    "items": [
      {
        "inventory_item_id": 1,
        "quantity": 50,
        "unit_of_measure": "kilogram",
        "estimated_price": 45.5,
        "notes": "Premium quality required"
      },
      {
        "inventory_item_id": 2,
        "quantity": 20,
        "unit_of_measure": "kilogram",
        "estimated_price": 60.0,
        "notes": ""
      }
    ]
  }'
```

### Approve Purchase Indent

**Endpoint:** `PUT /api/purchase/indents/{indent_id}/approve`

**Description:** Approve a purchase indent.

**Curl Example:**
```bash
curl -X PUT "http://localhost:8000/api/purchase/indents/1/approve" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Purchase Order

**Endpoint:** `POST /api/purchase/orders`

**Description:** Create a new purchase order.

**Request Body:**
```json
{
  "supplier_id": 1,
  "indent_id": 1,
  "order_date": "2025-10-16",
  "expected_delivery_date": "2025-10-25",
  "delivery_address": "Factory Address, City, PIN",
  "status": "pending",
  "payment_terms": "Net 30",
  "notes": "Please deliver during working hours",
  "items": [
    {
      "inventory_item_id": 1,
      "indent_item_id": 1,
      "quantity": 50,
      "unit_of_measure": "kilogram",
      "unit_price": 45.5,
      "tax_rate": 18.0,
      "discount_amount": 0,
      "hsn_code": "1701",
      "notes": ""
    },
    {
      "inventory_item_id": 2,
      "indent_item_id": 2,
      "quantity": 20,
      "unit_of_measure": "kilogram",
      "unit_price": 60.0,
      "tax_rate": 18.0,
      "discount_amount": 0,
      "hsn_code": "1702",
      "notes": ""
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/purchase/orders" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": 1,
    "indent_id": 1,
    "order_date": "2025-10-16",
    "expected_delivery_date": "2025-10-25",
    "delivery_address": "Factory Address, City, PIN",
    "status": "pending",
    "payment_terms": "Net 30",
    "notes": "Please deliver during working hours",
    "items": [
      {
        "inventory_item_id": 1,
        "indent_item_id": 1,
        "quantity": 50,
        "unit_of_measure": "kilogram",
        "unit_price": 45.5,
        "tax_rate": 18.0,
        "discount_amount": 0,
        "hsn_code": "1701",
        "notes": ""
      },
      {
        "inventory_item_id": 2,
        "indent_item_id": 2,
        "quantity": 20,
        "unit_of_measure": "kilogram",
        "unit_price": 60.0,
        "tax_rate": 18.0,
        "discount_amount": 0,
        "hsn_code": "1702",
        "notes": ""
      }
    ]
  }'
```

### Approve Purchase Order

**Endpoint:** `PUT /api/purchase/orders/{order_id}/approve`

**Description:** Approve a purchase order.

**Curl Example:**
```bash
curl -X PUT "http://localhost:8000/api/purchase/orders/1/approve" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Purchase Receipt

**Endpoint:** `POST /api/purchase/receipts`

**Description:** Create a new purchase receipt (goods receipt note).

**Request Body:**
```json
{
  "po_id": 1,
  "receipt_date": "2025-10-22",
  "supplier_invoice_number": "INV-12345",
  "supplier_invoice_date": "2025-10-22",
  "notes": "Goods received in good condition",
  "items": [
    {
      "po_item_id": 1,
      "received_quantity": 50,
      "accepted_quantity": 48,
      "rejected_quantity": 2,
      "rejection_reason": "Damaged packaging",
      "batch_number": "B12345",
      "expiry_date": "2026-10-22",
      "notes": ""
    },
    {
      "po_item_id": 2,
      "received_quantity": 20,
      "accepted_quantity": 20,
      "rejected_quantity": 0,
      "batch_number": "B12346",
      "expiry_date": "2026-10-22",
      "notes": ""
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/purchase/receipts" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "po_id": 1,
    "receipt_date": "2025-10-22",
    "supplier_invoice_number": "INV-12345",
    "supplier_invoice_date": "2025-10-22",
    "notes": "Goods received in good condition",
    "items": [
      {
        "po_item_id": 1,
        "received_quantity": 50,
        "accepted_quantity": 48,
        "rejected_quantity": 2,
        "rejection_reason": "Damaged packaging",
        "batch_number": "B12345",
        "expiry_date": "2026-10-22",
        "notes": ""
      },
      {
        "po_item_id": 2,
        "received_quantity": 20,
        "accepted_quantity": 20,
        "rejected_quantity": 0,
        "batch_number": "B12346",
        "expiry_date": "2026-10-22",
        "notes": ""
      }
    ]
  }'
```

## Production Management

### Create Bill of Material

**Endpoint:** `POST /api/production/bom`

**Description:** Create a new bill of material (recipe).

**Request Body:**
```json
{
  "product_id": 1,
  "name": "Standard Recipe",
  "description": "Standard recipe for product",
  "version": "1.0",
  "is_active": true,
  "items": [
    {
      "inventory_item_id": 1,
      "quantity": 0.5,
      "unit_of_measure": "kilogram",
      "notes": ""
    },
    {
      "inventory_item_id": 2,
      "quantity": 0.2,
      "unit_of_measure": "kilogram",
      "notes": ""
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/production/bom" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "name": "Standard Recipe",
    "description": "Standard recipe for product",
    "version": "1.0",
    "is_active": true,
    "items": [
      {
        "inventory_item_id": 1,
        "quantity": 0.5,
        "unit_of_measure": "kilogram",
        "notes": ""
      },
      {
        "inventory_item_id": 2,
        "quantity": 0.2,
        "unit_of_measure": "kilogram",
        "notes": ""
      }
    ]
  }'
```

### Create Production Batch

**Endpoint:** `POST /api/production/batches`

**Description:** Create a new production batch.

**Request Body:**
```json
{
  "product_id": 1,
  "bom_id": 1,
  "planned_quantity": 100,
  "production_date": "2025-10-25",
  "status": "planned",
  "notes": "Regular production batch",
  "packaged_items": [
    {
      "packaged_product_id": 1,
      "quantity": 50,
      "notes": "100g packages"
    },
    {
      "packaged_product_id": 2,
      "quantity": 25,
      "notes": "500g packages"
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/production/batches" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "bom_id": 1,
    "planned_quantity": 100,
    "production_date": "2025-10-25",
    "status": "planned",
    "notes": "Regular production batch",
    "packaged_items": [
      {
        "packaged_product_id": 1,
        "quantity": 50,
        "notes": "100g packages"
      },
      {
        "packaged_product_id": 2,
        "quantity": 25,
        "notes": "500g packages"
      }
    ]
  }'
```

### Start Production Batch

**Endpoint:** `PUT /api/production/batches/{batch_id}/start`

**Description:** Start a production batch, consuming raw materials.

**Curl Example:**
```bash
curl -X PUT "http://localhost:8000/api/production/batches/1/start" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Complete Production Batch

**Endpoint:** `PUT /api/production/batches/{batch_id}/complete`

**Description:** Complete a production batch, adding finished goods to inventory.

**Query Parameters:**
- `produced_quantity`: The actual quantity produced

**Curl Example:**
```bash
curl -X PUT "http://localhost:8000/api/production/batches/1/complete?produced_quantity=95" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Material Requirements

**Endpoint:** `GET /api/production/material-requirements`

**Description:** Calculate material requirements for producing a specific quantity of a product.

**Query Parameters:**
- `product_id`: Product ID
- `quantity`: Quantity to produce

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/production/material-requirements?product_id=1&quantity=100" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Gate Pass System

### Create Gate Pass

**Endpoint:** `POST /api/gate-pass`

**Description:** Create a new gate pass for inward or outward movement of goods.

**Request Body:**
```json
{
  "pass_type": "inward",
  "pass_date": "2025-10-22",
  "reference_number": "PO00001",
  "reference_type": "purchase_order",
  "reference_id": 1,
  "party_name": "ABC Suppliers",
  "vehicle_number": "KA01AB1234",
  "driver_name": "Raj Kumar",
  "driver_contact": "9876543210",
  "notes": "Regular delivery",
  "items": [
    {
      "item_type": "raw_material",
      "item_id": 1,
      "quantity": 50,
      "unit_of_measure": "kilogram",
      "description": "Sugar"
    },
    {
      "item_type": "raw_material",
      "item_id": 2,
      "quantity": 20,
      "unit_of_measure": "kilogram",
      "description": "Flour"
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/gate-pass" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pass_type": "inward",
    "pass_date": "2025-10-22",
    "reference_number": "PO00001",
    "reference_type": "purchase_order",
    "reference_id": 1,
    "party_name": "ABC Suppliers",
    "vehicle_number": "KA01AB1234",
    "driver_name": "Raj Kumar",
    "driver_contact": "9876543210",
    "notes": "Regular delivery",
    "items": [
      {
        "item_type": "raw_material",
        "item_id": 1,
        "quantity": 50,
        "unit_of_measure": "kilogram",
        "description": "Sugar"
      },
      {
        "item_type": "raw_material",
        "item_id": 2,
        "quantity": 20,
        "unit_of_measure": "kilogram",
        "description": "Flour"
      }
    ]
  }'
```

### Approve Gate Pass

**Endpoint:** `PUT /api/gate-pass/{gate_pass_id}/approve`

**Description:** Approve a gate pass.

**Curl Example:**
```bash
curl -X PUT "http://localhost:8000/api/gate-pass/1/approve" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Print Gate Pass

**Endpoint:** `GET /api/gate-pass/print/{gate_pass_id}`

**Description:** Get formatted data for printing a gate pass.

**Curl Example:**
```bash
curl -X GET "http://localhost:8000/api/gate-pass/print/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```


[//]: # (rm -rf .aws-sam/build  )
[//]: # (sam build  )
[//]: # (sam deploy --guided --profile target-account)