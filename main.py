from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from sqlalchemy.orm import Session
import logging
import sys
import os


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from app.database import get_db
# Import models to ensure they're registered with SQLAlchemy
from app.models import *
from app.routers import auth, users, products, categories, cart, admin, seller, seller_api, seo, tax, logistics, payments, invoices, testimonials, blogs, shipping_methods, payment_methods, addresses, checkout, orders, inventory, packaged_products, purchase, production, gate_pass, razorpay_webhook, razorpay_orders, user_permissions
from app.utils.keep_alive import start_keep_alive

app = FastAPI(
    title="Azlok Enterprises API",
    description="API for Azlok Enterprises E-commerce Platform",
    version="1.0.0",
    debug=True
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

handler = Mangum(app)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(addresses.router, prefix="/api/users/addresses", tags=["Addresses"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
# Orders router temporarily removed
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(seller_api.router, prefix="/api/seller", tags=["Seller API"])
app.include_router(tax.router, prefix="/api/tax", tags=["Tax"])
app.include_router(logistics.router, prefix="/api/logistics", tags=["Logistics"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(razorpay_webhook.router, prefix="/api/razorpay", tags=["Razorpay"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Invoices"])
app.include_router(testimonials.router, prefix="/api/testimonials", tags=["Testimonials"])
app.include_router(blogs.router, prefix="/api/blogs", tags=["Blogs"])
app.include_router(shipping_methods.router, prefix="/api/shipping", tags=["Shipping"])
app.include_router(payment_methods.router, prefix="/api/payment-methods", tags=["Payment Methods"])
app.include_router(checkout.router, prefix="/api/cart-summary", tags=["Checkout Summary"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(packaged_products.router, prefix="/packaged-products", tags=["packaged-products"])
app.include_router(purchase.router, prefix="/purchase", tags=["purchase"])
app.include_router(production.router, prefix="/production", tags=["production"])
app.include_router(gate_pass.router, prefix="/gate-pass", tags=["gate-pass"])
# SEO router - no prefix as these are root-level endpoints
app.include_router(seo.router, tags=["SEO"])
app.include_router(razorpay_orders.router, prefix="/api/payments", tags=["Razorpay Orders"])
app.include_router(user_permissions.router, prefix="/api/permissions", tags=["User Permissions"])

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Azlok Enterprises API",
        "version": "1.0.1",
        "updated": "2026-01-15"
    }

@app.get("/health")
def health_check():
    # Use datetime instead of asyncio.get_event_loop() to avoid event loop errors
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/debug/db-info")
def debug_db_info():
    """Debug endpoint to check database connection"""
    from app.database import DATABASE_URL
    import os
    
    # Mask password in URL for security
    db_url_masked = DATABASE_URL
    if "@" in db_url_masked:
        parts = db_url_masked.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split("://")[1]
            if ":" in user_pass:
                user = user_pass.split(":")[0]
                db_url_masked = db_url_masked.replace(user_pass, f"{user}:****")
    
    return {
        "database_url": db_url_masked,
        "has_env_override": "DATABASE_URL" in os.environ,
        "env_database_url": os.getenv("DATABASE_URL", "Not set")[:50] + "..." if os.getenv("DATABASE_URL") else "Not set"
    }

# Keep-alive background task
@app.on_event("startup")
async def startup_event():
    # Only start the keep-alive service if we're in production (on Render)
    if os.getenv("RENDER", "false").lower() == "true":
        # Start the keep-alive service in the background
        import asyncio
        asyncio.create_task(start_keep_alive())
        logging.info("Keep-alive service started")

# Graceful shutdown
@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Application shutting down")

# if __name__ == "__main__":
#     import uvicorn
#     # Get port from environment variable for Render compatibility
#     port = int(os.environ.get("PORT", 8000))
#     uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
