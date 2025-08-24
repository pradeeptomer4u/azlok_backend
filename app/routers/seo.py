from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from .. import models
from ..database import get_db
from ..utils.sitemap_generator import SitemapGenerator, get_sitemap_generator

router = APIRouter()


@router.get("/sitemap.xml", response_class=Response)
async def get_sitemap(
    request: Request,
    sitemap_generator: SitemapGenerator = Depends(get_sitemap_generator),
):
    """
    Generate and return the sitemap XML.
    """
    # Get base URL from request
    base_url = str(request.base_url).rstrip('/')
    
    # Override the base URL in the sitemap generator
    sitemap_generator.base_url = base_url
    
    # Generate the sitemap
    sitemap_xml = sitemap_generator.generate_sitemap()
    
    # Return XML response
    return Response(
        content=sitemap_xml,
        media_type="application/xml"
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def get_robots_txt(request: Request):
    """
    Generate and return the robots.txt file.
    """
    base_url = str(request.base_url).rstrip('/')
    
    robots_txt = f"""# Robots.txt for Marketplace
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /seller/dashboard/
Disallow: /api/
Disallow: /auth/
Disallow: /cart/checkout/
Disallow: /user/profile/

# Sitemaps
Sitemap: {base_url}/sitemap.xml
"""
    
    return PlainTextResponse(content=robots_txt)


@router.get("/meta-tags", response_model=dict)
async def get_meta_tags(
    page_type: str,
    object_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get meta tags for different page types.
    
    Args:
        page_type: Type of page (home, product, category, etc.)
        object_id: ID of the object (product ID, category ID, etc.)
    """
    meta_tags = {
        "title": "Marketplace - Shop Online",
        "description": "Find the best products from trusted sellers.",
        "keywords": "marketplace, online shopping, ecommerce",
        "og:type": "website",
        "og:url": "",
        "og:title": "Marketplace - Shop Online",
        "og:description": "Find the best products from trusted sellers.",
        "og:image": "/logo.png",
        "twitter:card": "summary_large_image",
        "twitter:title": "Marketplace - Shop Online",
        "twitter:description": "Find the best products from trusted sellers.",
        "twitter:image": "/logo.png",
    }
    
    if page_type == "product" and object_id:
        product = db.query(models.Product).filter(models.Product.id == object_id).first()
        if product:
            meta_tags["title"] = f"{product.name} | Marketplace"
            meta_tags["description"] = product.description[:160] + "..." if len(product.description) > 160 else product.description
            meta_tags["keywords"] = f"{product.name}, {product.category.name}, marketplace, online shopping"
            meta_tags["og:url"] = f"/product/{product.slug}"
            meta_tags["og:title"] = product.name
            meta_tags["og:description"] = product.description[:160] + "..." if len(product.description) > 160 else product.description
            meta_tags["og:image"] = product.image_url if product.image_url else "/logo.png"
            meta_tags["twitter:title"] = product.name
            meta_tags["twitter:description"] = product.description[:160] + "..." if len(product.description) > 160 else product.description
            meta_tags["twitter:image"] = product.image_url if product.image_url else "/logo.png"
    
    elif page_type == "category" and object_id:
        category = db.query(models.Category).filter(models.Category.id == object_id).first()
        if category:
            meta_tags["title"] = f"{category.name} | Marketplace"
            meta_tags["description"] = f"Shop {category.name} products on Marketplace. Find the best deals on {category.name}."
            meta_tags["keywords"] = f"{category.name}, marketplace, online shopping"
            meta_tags["og:url"] = f"/category/{category.slug}"
            meta_tags["og:title"] = f"{category.name} | Marketplace"
            meta_tags["og:description"] = f"Shop {category.name} products on Marketplace. Find the best deals on {category.name}."
            meta_tags["twitter:title"] = f"{category.name} | Marketplace"
            meta_tags["twitter:description"] = f"Shop {category.name} products on Marketplace. Find the best deals on {category.name}."
    
    return meta_tags
