"""
Database Schemas for Digital Library

Each Pydantic model maps to a MongoDB collection (lowercased class name):
- Book -> "book"
- Member -> "member"
- Loan -> "loan"

These are used for validation and also surfaced via GET /schema for the database viewer.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import date, datetime


class Book(BaseModel):
    """
    Books collection schema
    Collection: "book"
    """
    title: str = Field(..., description="Book title")
    author: str = Field(..., description="Author name")
    isbn: Optional[str] = Field(None, description="ISBN number")
    published_year: Optional[int] = Field(None, ge=0, le=2100, description="Year published")
    categories: List[str] = Field(default_factory=list, description="Categories/genres")
    description: Optional[str] = Field(None, description="Brief description")
    copies_total: int = Field(1, ge=0, description="Total copies owned")
    copies_available: int = Field(1, ge=0, description="Copies currently available")


class Member(BaseModel):
    """
    Members collection schema
    Collection: "member"
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    membership_id: Optional[str] = Field(None, description="External membership ID")
    phone: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(True, description="Active membership")


class Loan(BaseModel):
    """
    Loans collection schema
    Collection: "loan"
    """
    book_id: str = Field(..., description="ID of the book")
    member_id: str = Field(..., description="ID of the member")
    loan_date: Optional[datetime] = Field(None, description="Loan date (default now)")
    due_date: Optional[date] = Field(None, description="Due date")
    return_date: Optional[datetime] = Field(None, description="Return date if returned")
    status: str = Field("borrowed", description="borrowed | returned | overdue")
