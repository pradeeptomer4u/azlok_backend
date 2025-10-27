#!/usr/bin/env python3
"""
Script to import product details from a JSON file.
"""
import os
import sys
import json
import re
import argparse
from datetime import datetime

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.database import SessionLocal, engine, Base
from app.models import Product, ProductNutritionalDetail


def extract_url(markdown_url):
    """Extract URL from markdown format: [text](url)"""
    if not markdown_url:
        return None
    url_match = re.search(r'\]\((.*?)\)', markdown_url)
    if url_match:
        return url_match.group(1)
    return markdown_url


def import_product_details(json_file_path):
    """Import product details from a JSON file."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Open database session
    db = SessionLocal()

    try:
        # Load JSON data
        print(f"Loading data from {json_file_path}...")
        with open(json_file_path, 'r') as file:
            data = json.load(file)

        print(f"Found {len(data)} product details to import.")

        total_imported = 0
        total_skipped = 0
        total_updated = 0

        for item in data:
            try:
                # Check for required fields
                slug = item.get("slug")
                if not slug:
                    print(f"Skipping item without slug")
                    total_skipped += 1
                    continue

                # Find the product by slug
                product = db.query(Product).filter(Product.slug == slug).first()
                if not product:
                    print(f"Skipping unknown product slug: {slug}")
                    total_skipped += 1
                    continue

                # Check if product detail already exists
                existing_detail = db.query(ProductNutritionalDetail).filter(
                    ProductNutritionalDetail.product_id == product.id
                ).first()

                # Process URLs in source_wikipedia and research_papers
                source_wikipedia_urls = []
                if isinstance(item.get("source_wikipedia"), list):
                    source_wikipedia_urls = [extract_url(url) for url in item.get("source_wikipedia") if url]

                research_paper_urls = []
                if isinstance(item.get("research_papers"), list):
                    research_paper_urls = [extract_url(url) for url in item.get("research_papers") if url]

                # Extract URL from source_url if it's in markdown format
                source_url = None
                if item.get("source_url"):
                    source_url = extract_url(item.get("source_url"))

                # Convert string fields to arrays for database compatibility
                health_benefits = item.get("health_benefits")
                if health_benefits and isinstance(health_benefits, str):
                    health_benefits = [health_benefits]

                contraindications = item.get("contraindications")
                if contraindications and isinstance(contraindications, str):
                    contraindications = [contraindications]

                # Map fields with values and units separately
                detail_data = {
                    "product_id": product.id,

                    # Source information
                    "source_region": item.get("source_region"),
                    "source_wikipedia": source_wikipedia_urls,
                    "source_url": source_url,
                    "manufacturing_process": item.get("manufacturing_process"),

                    # Handle research papers as simple array of links
                    "research_papers": research_paper_urls,

                    # Nutrition data
                    "calories": item.get("calories"),
                    "calories_unit": item.get("calories_unit"),
                    "protein": item.get("protein"),
                    "protein_unit": item.get("protein_unit"),
                    "carbohydrates": item.get("carbohydrates"),
                    "carbohydrates_unit": item.get("carbohydrates_unit"),
                    "total_fat": item.get("total_fat"),
                    "total_fat_unit": item.get("total_fat_unit"),
                    "fiber": item.get("fiber"),
                    "fiber_unit": item.get("fiber_unit"),
                    "sugar": item.get("sugar"),
                    "sugar_unit": item.get("sugar_unit"),
                    "sodium": item.get("sodium"),
                    "sodium_unit": item.get("sodium_unit"),

                    # Additional minerals
                    "potassium": item.get("potassium"),
                    "potassium_unit": item.get("potassium_unit"),
                    "calcium": item.get("calcium"),
                    "calcium_unit": item.get("calcium_unit"),
                    "iron": item.get("iron"),
                    "iron_unit": item.get("iron_unit"),
                    "magnesium": item.get("magnesium"),
                    "magnesium_unit": item.get("magnesium_unit"),
                    "phosphorus": item.get("phosphorus"),
                    "phosphorus_unit": item.get("phosphorus_unit"),
                    "zinc": item.get("zinc"),
                    "zinc_unit": item.get("zinc_unit"),

                    # Vitamins
                    "vitamin_a": item.get("vitamin_a"),
                    "vitamin_a_unit": item.get("vitamin_a_unit"),
                    "vitamin_c": item.get("vitamin_c"),
                    "vitamin_c_unit": item.get("vitamin_c_unit"),
                    "vitamin_d": item.get("vitamin_d"),
                    "vitamin_d_unit": item.get("vitamin_d_unit"),
                    "vitamin_e": item.get("vitamin_e"),
                    "vitamin_e_unit": item.get("vitamin_e_unit"),
                    "vitamin_k": item.get("vitamin_k"),
                    "vitamin_k_unit": item.get("vitamin_k_unit"),
                    "thiamin": item.get("thiamin"),
                    "thiamin_unit": item.get("thiamin_unit"),
                    "riboflavin": item.get("riboflavin"),
                    "riboflavin_unit": item.get("riboflavin_unit"),
                    "niacin": item.get("niacin"),
                    "niacin_unit": item.get("niacin_unit"),
                    "vitamin_b6": item.get("vitamin_b6"),
                    "vitamin_b6_unit": item.get("vitamin_b6_unit"),
                    "folate": item.get("folate"),
                    "folate_unit": item.get("folate_unit"),
                    "vitamin_b12": item.get("vitamin_b12"),
                    "vitamin_b12_unit": item.get("vitamin_b12_unit"),

                    # Additional nutritional information
                    "glycemic_index": item.get("glycemic_index"),
                    "antioxidants": item.get("antioxidants"),
                    "allergens": item.get("allergens"),

                    # Additional fields for fats breakdown
                    "saturated_fat": item.get("saturated_fat"),
                    "saturated_fat_unit": item.get("saturated_fat_unit"),
                    "monounsaturated_fat": item.get("monounsaturated_fat"),
                    "monounsaturated_fat_unit": item.get("monounsaturated_fat_unit"),
                    "polyunsaturated_fat": item.get("polyunsaturated_fat"),
                    "polyunsaturated_fat_unit": item.get("polyunsaturated_fat_unit"),
                    "trans_fat": item.get("trans_fat"),
                    "trans_fat_unit": item.get("trans_fat_unit"),
                    "cholesterol": item.get("cholesterol"),
                    "cholesterol_unit": item.get("cholesterol_unit"),

                    # Additional fields for carbs breakdown
                    "dietary_fiber": item.get("dietary_fiber"),
                    "dietary_fiber_unit": item.get("dietary_fiber_unit"),
                    "soluble_fiber": item.get("soluble_fiber"),
                    "soluble_fiber_unit": item.get("soluble_fiber_unit"),
                    "insoluble_fiber": item.get("insoluble_fiber"),
                    "insoluble_fiber_unit": item.get("insoluble_fiber_unit"),

                    # Units of measurement
                    "serving_size": item.get("serving_size"),
                    "serving_unit": item.get("serving_unit"),

                    # Additional information - convert strings to arrays for database compatibility
                    "notes": item.get("notes"),
                    "health_benefits": health_benefits,
                    "contraindications": contraindications,
                }

                # Remove None values to avoid overwriting existing data with None
                detail_data = {k: v for k, v in detail_data.items() if v is not None}

                if existing_detail:
                    # Update existing detail
                    for key, value in detail_data.items():
                        setattr(existing_detail, key, value)

                    existing_detail.updated_at = datetime.utcnow().isoformat()
                    total_updated += 1
                    print(f"Updated details for product: {slug}")
                else:
                    # Create new detail
                    db_detail = ProductNutritionalDetail(**detail_data)
                    db.add(db_detail)
                    total_imported += 1
                    print(f"Imported details for product: {slug}")

                # Commit after each product to avoid losing all data if an error occurs
                db.commit()

            except Exception as e:
                db.rollback()
                print(f"Error processing item with slug {item.get('slug', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
                total_skipped += 1
                # Continue with the next item instead of failing the entire import
                continue

        print(
            f"Import completed. Total products: imported={total_imported}, updated={total_updated}, skipped={total_skipped}")

    except Exception as e:
        db.rollback()
        print(f"Error importing data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def main():
    """Main function to parse command-line arguments and run the import."""

    import_product_details("/Users/pradeep/Library/Application Support/JetBrains/PyCharm2024.3/scratches/scratch.json")


if __name__ == "__main__":
    main()