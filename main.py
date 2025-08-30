from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from app.database import get_db
from app.routers import auth, users, products, categories, cart, admin, seller, seller_api, seo, tax, logistics, payments, invoices, testimonials

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

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
# Orders router temporarily removed
# app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(seller_api.router, prefix="/api/seller", tags=["Seller API"])
app.include_router(tax.router, prefix="/api/tax", tags=["Tax"])
app.include_router(logistics.router, prefix="/api/logistics", tags=["Logistics"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Invoices"])
app.include_router(testimonials.router, prefix="/api/testimonials", tags=["Testimonials"])

# SEO router - no prefix as these are root-level endpoints
app.include_router(seo.router, tags=["SEO"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Azlok Enterprises API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
