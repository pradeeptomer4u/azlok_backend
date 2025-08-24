from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# Create router
router = APIRouter()

# Testimonial model
class Testimonial(BaseModel):
    id: int
    name: str
    company: str
    image: str
    testimonial: str
    rating: float
    date: str
    verified: bool

# Mock testimonial data
mock_testimonials = [
    {
        "id": 1,
        "name": "Rahul Sharma",
        "company": "Tech Solutions Ltd",
        "image": "/globe.svg",
        "testimonial": "Azlok has been a game-changer for our business. The quality of products and reliability of service is unmatched in the industry.",
        "rating": 5.0,
        "date": "2023-06-15",
        "verified": True
    },
    {
        "id": 2,
        "name": "Priya Patel",
        "company": "Innovate Designs",
        "image": "/globe.svg",
        "testimonial": "We have been sourcing materials from Azlok for over two years now. Their consistent quality and on-time delivery have helped us grow our business significantly.",
        "rating": 4.5,
        "date": "2023-05-22",
        "verified": True
    },
    {
        "id": 3,
        "name": "Amit Kumar",
        "company": "Global Traders",
        "image": "/globe.svg",
        "testimonial": "The customer service at Azlok is exceptional. They go above and beyond to ensure customer satisfaction. Highly recommended!",
        "rating": 5.0,
        "date": "2023-04-10",
        "verified": True
    },
    {
        "id": 4,
        "name": "Sneha Gupta",
        "company": "Creative Solutions",
        "image": "/globe.svg",
        "testimonial": "Azlok offers a wide range of high-quality products at competitive prices. Their platform is user-friendly and makes procurement a breeze.",
        "rating": 4.0,
        "date": "2023-03-05",
        "verified": True
    },
    {
        "id": 5,
        "name": "Vikram Singh",
        "company": "Modern Enterprises",
        "image": "/globe.svg",
        "testimonial": "I've been using Azlok for my business needs for the past year. The product quality and customer service have been consistently excellent.",
        "rating": 4.8,
        "date": "2023-02-18",
        "verified": True
    },
    {
        "id": 6,
        "name": "Neha Kapoor",
        "company": "Design Hub",
        "image": "/globe.svg",
        "testimonial": "Azlok has streamlined our procurement process. Their platform is intuitive and their customer support team is always ready to help.",
        "rating": 4.7,
        "date": "2023-01-30",
        "verified": True
    }
]

@router.get("", response_model=List[Testimonial])
async def get_all_testimonials():
    """Get all testimonials"""
    return mock_testimonials

@router.get("/featured", response_model=List[Testimonial])
async def get_featured_testimonials(limit: int = Query(4, ge=1, le=10)):
    """Get featured testimonials with optional limit"""
    # Return top rated testimonials as featured
    sorted_testimonials = sorted(mock_testimonials, key=lambda x: x["rating"], reverse=True)
    return sorted_testimonials[:limit]

@router.get("/{testimonial_id}", response_model=Testimonial)
async def get_testimonial_by_id(testimonial_id: int):
    """Get a specific testimonial by ID"""
    for testimonial in mock_testimonials:
        if testimonial["id"] == testimonial_id:
            return testimonial
    raise HTTPException(status_code=404, detail="Testimonial not found")
