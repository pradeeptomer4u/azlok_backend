import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import Depends

from .. import models
from ..database import get_db


class SitemapGenerator:
    """
    Utility class for generating XML sitemaps for the website.
    """
    
    def __init__(self, db: Session, base_url: str):
        """
        Initialize the sitemap generator.
        
        Args:
            db: Database session
            base_url: Base URL of the website (e.g., https://example.com)
        """
        self.db = db
        self.base_url = base_url.rstrip('/')
        
    def generate_sitemap(self) -> str:
        """
        Generate a complete sitemap XML for the website.
        
        Returns:
            str: XML sitemap as a string
        """
        # Create root element
        urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        
        # Add static pages
        self._add_static_pages(urlset)
        
        # Add dynamic pages
        self._add_category_pages(urlset)
        self._add_product_pages(urlset)
        
        # Convert to string
        return ET.tostring(urlset, encoding='utf-8', method='xml').decode('utf-8')
    
    def generate_sitemap_index(self, sitemaps: List[Dict[str, str]]) -> str:
        """
        Generate a sitemap index XML.
        
        Args:
            sitemaps: List of dictionaries with 'loc' and 'lastmod' keys
            
        Returns:
            str: XML sitemap index as a string
        """
        # Create root element
        sitemapindex = ET.Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        
        # Add sitemap entries
        for sitemap in sitemaps:
            sitemap_elem = ET.SubElement(sitemapindex, "sitemap")
            ET.SubElement(sitemap_elem, "loc").text = sitemap['loc']
            ET.SubElement(sitemap_elem, "lastmod").text = sitemap['lastmod']
        
        # Convert to string
        return ET.tostring(sitemapindex, encoding='utf-8', method='xml').decode('utf-8')
    
    def _add_static_pages(self, urlset: ET.Element) -> None:
        """
        Add static pages to the sitemap.
        
        Args:
            urlset: Root urlset element
        """
        static_pages = [
            {"url": "/", "priority": "1.0", "changefreq": "daily"},
            {"url": "/about", "priority": "0.8", "changefreq": "monthly"},
            {"url": "/contact", "priority": "0.8", "changefreq": "monthly"},
            {"url": "/terms", "priority": "0.5", "changefreq": "monthly"},
            {"url": "/privacy", "priority": "0.5", "changefreq": "monthly"},
            {"url": "/faq", "priority": "0.7", "changefreq": "weekly"},
        ]
        
        for page in static_pages:
            url_elem = ET.SubElement(urlset, "url")
            ET.SubElement(url_elem, "loc").text = f"{self.base_url}{page['url']}"
            ET.SubElement(url_elem, "priority").text = page["priority"]
            ET.SubElement(url_elem, "changefreq").text = page["changefreq"]
            ET.SubElement(url_elem, "lastmod").text = datetime.utcnow().strftime("%Y-%m-%d")
    
    def _add_category_pages(self, urlset: ET.Element) -> None:
        """
        Add category pages to the sitemap.
        
        Args:
            urlset: Root urlset element
        """
        categories = self.db.query(models.Category).all()
        
        for category in categories:
            url_elem = ET.SubElement(urlset, "url")
            ET.SubElement(url_elem, "loc").text = f"{self.base_url}/category/{category.slug}"
            ET.SubElement(url_elem, "priority").text = "0.8"
            ET.SubElement(url_elem, "changefreq").text = "weekly"
            
            # Use updated_at if available, otherwise use current date
            lastmod = category.updated_at if hasattr(category, 'updated_at') else datetime.utcnow()
            ET.SubElement(url_elem, "lastmod").text = lastmod.strftime("%Y-%m-%d")
    
    def _add_product_pages(self, urlset: ET.Element) -> None:
        """
        Add product pages to the sitemap.
        
        Args:
            urlset: Root urlset element
        """
        # Only include approved products
        products = self.db.query(models.Product).filter(
            models.Product.approval_status == models.ApprovalStatus.APPROVED
        ).all()
        
        for product in products:
            url_elem = ET.SubElement(urlset, "url")
            ET.SubElement(url_elem, "loc").text = f"{self.base_url}/product/{product.slug}"
            ET.SubElement(url_elem, "priority").text = "0.9"
            ET.SubElement(url_elem, "changefreq").text = "daily"
            
            # Use updated_at if available, otherwise use current date
            lastmod = product.updated_at if hasattr(product, 'updated_at') else datetime.utcnow()
            ET.SubElement(url_elem, "lastmod").text = lastmod.strftime("%Y-%m-%d")


def get_sitemap_generator(
    db: Session = Depends(get_db),
    base_url: str = "https://marketplace.example.com"
) -> SitemapGenerator:
    """
    Dependency for getting a sitemap generator instance.
    
    Args:
        db: Database session
        base_url: Base URL of the website
        
    Returns:
        SitemapGenerator: An instance of the sitemap generator
    """
    return SitemapGenerator(db, base_url)
