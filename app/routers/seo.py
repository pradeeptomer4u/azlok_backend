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


# Static Pages
@router.get("/static-pages/{page_name}", response_model=dict)
async def get_static_page(page_name: str):
    """
    Get content for static pages like about, brands, shipping, etc.
    """
    # Define content for different static pages
    static_pages = {
        "about": {
            "title": "About Azlok",
            "content": [
                {
                    "type": "heading",
                    "text": "About Azlok Enterprises"
                },
                {
                    "type": "paragraph",
                    "text": "Azlok Enterprises is a leading e-commerce platform connecting buyers and sellers across India. Founded in 2020, we've grown to become one of the most trusted marketplaces for quality products."
                },
                {
                    "type": "heading",
                    "text": "Our Mission"
                },
                {
                    "type": "paragraph",
                    "text": "To create a seamless and reliable online marketplace that empowers businesses and provides customers with access to quality products at competitive prices."
                },
                {
                    "type": "heading",
                    "text": "Our Vision"
                },
                {
                    "type": "paragraph",
                    "text": "To be the most trusted e-commerce platform in India, known for our commitment to quality, reliability, and customer satisfaction."
                }
            ],
            "meta": {
                "title": "About Us | Azlok Enterprises",
                "description": "Learn about Azlok Enterprises, our mission, vision, and commitment to quality e-commerce services in India.",
                "keywords": "about azlok, azlok enterprises, e-commerce platform, online marketplace"
            }
        },
        "brands": {
            "title": "Our Brands",
            "content": [
                {
                    "type": "heading",
                    "text": "Featured Brands on Azlok"
                },
                {
                    "type": "paragraph",
                    "text": "Azlok partners with some of the most reputable brands in India and internationally. We carefully vet all our brand partners to ensure they meet our high standards for quality and customer service."
                },
                {
                    "type": "brands",
                    "items": [
                        {"name": "Tech Solutions Ltd", "logo": "/globe.svg", "description": "Leading technology solutions provider"},
                        {"name": "Innovate Designs", "logo": "/globe.svg", "description": "Creative design solutions for modern businesses"},
                        {"name": "Global Traders", "logo": "/globe.svg", "description": "International trading company with premium products"},
                        {"name": "Creative Solutions", "logo": "/globe.svg", "description": "Innovative solutions for everyday challenges"},
                        {"name": "Modern Enterprises", "logo": "/globe.svg", "description": "Contemporary business solutions and products"},
                        {"name": "Design Hub", "logo": "/globe.svg", "description": "Hub for all design-related products and services"}
                    ]
                }
            ],
            "meta": {
                "title": "Our Brands | Azlok Enterprises",
                "description": "Discover the premium brands available on Azlok Enterprises. Shop products from trusted manufacturers and sellers.",
                "keywords": "azlok brands, premium brands, trusted sellers, quality products"
            }
        },
        "shipping": {
            "title": "Shipping & Delivery",
            "content": [
                {
                    "type": "heading",
                    "text": "Shipping & Delivery Information"
                },
                {
                    "type": "paragraph",
                    "text": "At Azlok, we strive to deliver your orders promptly and securely. We partner with trusted logistics providers to ensure your purchases reach you in perfect condition."
                },
                {
                    "type": "heading",
                    "text": "Delivery Timeframes"
                },
                {
                    "type": "list",
                    "items": [
                        "Metro Cities: 2-3 business days",
                        "Tier 2 Cities: 3-5 business days",
                        "Other Locations: 5-7 business days"
                    ]
                },
                {
                    "type": "heading",
                    "text": "Shipping Costs"
                },
                {
                    "type": "paragraph",
                    "text": "Shipping costs are calculated based on the delivery location, package weight, and dimensions. Free shipping is available on orders above ₹1000."
                }
            ],
            "meta": {
                "title": "Shipping & Delivery | Azlok Enterprises",
                "description": "Learn about Azlok's shipping policies, delivery timeframes, and costs. Get information on how we deliver products across India.",
                "keywords": "azlok shipping, delivery policy, shipping costs, delivery timeframes"
            }
        },
        "returns": {
            "title": "Returns & Refunds",
            "content": [
                {
                    "type": "heading",
                    "text": "Returns & Refunds Policy"
                },
                {
                    "type": "paragraph",
                    "text": "We want you to be completely satisfied with your purchases from Azlok. If you're not happy with your order, we offer a hassle-free return and refund process."
                },
                {
                    "type": "heading",
                    "text": "Return Eligibility"
                },
                {
                    "type": "list",
                    "items": [
                        "Products must be returned within 7 days of delivery",
                        "Items must be unused and in original packaging",
                        "Proof of purchase is required",
                        "Some categories like perishables and customized items are not eligible for return"
                    ]
                },
                {
                    "type": "heading",
                    "text": "Refund Process"
                },
                {
                    "type": "paragraph",
                    "text": "Once we receive and inspect the returned item, we will process your refund. The amount will be credited back to your original payment method within 5-7 business days."
                }
            ],
            "meta": {
                "title": "Returns & Refunds | Azlok Enterprises",
                "description": "Learn about Azlok's return and refund policies. Find out how to return products and get refunds for your purchases.",
                "keywords": "azlok returns, refund policy, return process, product returns"
            }
        },
        "privacy": {
            "title": "Privacy Policy",
            "content": [
                {
                    "type": "heading",
                    "text": "Privacy Policy"
                },
                {
                    "type": "paragraph",
                    "text": "At Azlok, we take your privacy seriously. This policy outlines how we collect, use, and protect your personal information when you use our platform."
                },
                {
                    "type": "heading",
                    "text": "Information We Collect"
                },
                {
                    "type": "list",
                    "items": [
                        "Personal information (name, email, phone number, address)",
                        "Payment information",
                        "Browsing behavior and preferences",
                        "Device information"
                    ]
                },
                {
                    "type": "heading",
                    "text": "How We Use Your Information"
                },
                {
                    "type": "paragraph",
                    "text": "We use your information to process orders, improve our services, personalize your shopping experience, and communicate with you about your orders and promotions."
                },
                {
                    "type": "heading",
                    "text": "Data Security"
                },
                {
                    "type": "paragraph",
                    "text": "We implement robust security measures to protect your personal information from unauthorized access, alteration, disclosure, or destruction."
                }
            ],
            "meta": {
                "title": "Privacy Policy | Azlok Enterprises",
                "description": "Read Azlok's privacy policy to understand how we collect, use, and protect your personal information.",
                "keywords": "azlok privacy policy, data protection, personal information, privacy"
            }
        },
        "terms": {
            "title": "Terms & Conditions",
            "content": [
                {
                    "type": "heading",
                    "text": "Terms & Conditions"
                },
                {
                    "type": "paragraph",
                    "text": "By using the Azlok platform, you agree to these terms and conditions. Please read them carefully before using our services."
                },
                {
                    "type": "heading",
                    "text": "User Accounts"
                },
                {
                    "type": "paragraph",
                    "text": "You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account."
                },
                {
                    "type": "heading",
                    "text": "Product Listings"
                },
                {
                    "type": "paragraph",
                    "text": "We strive to provide accurate product information, but we do not warrant that product descriptions or other content is accurate, complete, reliable, current, or error-free."
                },
                {
                    "type": "heading",
                    "text": "Intellectual Property"
                },
                {
                    "type": "paragraph",
                    "text": "All content on the Azlok platform, including text, graphics, logos, and software, is the property of Azlok or its content suppliers and is protected by copyright laws."
                }
            ],
            "meta": {
                "title": "Terms & Conditions | Azlok Enterprises",
                "description": "Read Azlok's terms and conditions to understand the rules and guidelines for using our platform.",
                "keywords": "azlok terms, conditions, user agreement, platform rules"
            }
        },
        "contact": {
            "title": "Contact Us",
            "content": [
                {
                    "type": "heading",
                    "text": "Contact Azlok Enterprises"
                },
                {
                    "type": "paragraph",
                    "text": "We're here to help! If you have any questions, concerns, or feedback, please don't hesitate to reach out to us."
                },
                {
                    "type": "contact_info",
                    "items": [
                        {"type": "email", "label": "Customer Support", "value": "support@azlok.com"},
                        {"type": "email", "label": "Business Inquiries", "value": "business@azlok.com"},
                        {"type": "phone", "label": "Customer Service", "value": "+91-1234567890"},
                        {"type": "address", "label": "Headquarters", "value": "123 Commerce Street, Tech Park, Bangalore - 560001, Karnataka, India"}
                    ]
                },
                {
                    "type": "heading",
                    "text": "Business Hours"
                },
                {
                    "type": "paragraph",
                    "text": "Our customer service team is available Monday through Saturday, 9:00 AM to 6:00 PM IST."
                }
            ],
            "meta": {
                "title": "Contact Us | Azlok Enterprises",
                "description": "Get in touch with Azlok Enterprises. Find our contact information, business hours, and ways to reach our customer support team.",
                "keywords": "contact azlok, customer support, azlok contact information, help"
            }
        }
    }
    
    # Return the requested page or a 404 response
    if page_name in static_pages:
        return static_pages[page_name]
    else:
        # Return a generic page for any missing static pages
        return {
            "title": "Page Not Found",
            "content": [
                {
                    "type": "heading",
                    "text": "Page Not Found"
                },
                {
                    "type": "paragraph",
                    "text": "The page you are looking for does not exist or has been moved."
                }
            ],
            "meta": {
                "title": "Page Not Found | Azlok Enterprises",
                "description": "The requested page could not be found on Azlok Enterprises.",
                "keywords": "page not found, 404, error"
            }
        }
