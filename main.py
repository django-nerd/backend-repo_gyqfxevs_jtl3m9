import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI(title="Digital Library API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BookIn(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    published_year: Optional[int] = None
    categories: List[str] = []
    description: Optional[str] = None
    copies_total: int = 1


class MemberIn(BaseModel):
    name: str
    email: str
    membership_id: Optional[str] = None
    phone: Optional[str] = None


class LoanIn(BaseModel):
    book_id: str
    member_id: str
    days: int = 14


@app.get("/")
def read_root():
    return {"message": "Digital Library Backend is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Books endpoints
@app.post("/api/books")
def add_book(payload: BookIn):
    data = payload.model_dump()
    data["copies_available"] = payload.copies_total
    book_id = create_document("book", data)
    return {"id": book_id}


@app.get("/api/books")
def list_books(q: Optional[str] = None):
    filter_dict = {}
    if q:
        # naive text search across title/author
        filter_dict = {"$or": [
            {"title": {"$regex": q, "$options": "i"}},
            {"author": {"$regex": q, "$options": "i"}},
            {"categories": {"$elemMatch": {"$regex": q, "$options": "i"}}}
        ]}
    books = get_documents("book", filter_dict)
    for b in books:
        b["_id"] = str(b.get("_id"))
    return books


# Members endpoints
@app.post("/api/members")
def add_member(payload: MemberIn):
    member_id = create_document("member", payload)
    return {"id": member_id}


@app.get("/api/members")
def list_members():
    members = get_documents("member")
    for m in members:
        m["_id"] = str(m.get("_id"))
    return members


# Loans endpoints
from bson import ObjectId


def _get_by_id(collection: str, id_str: str):
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db[collection].find_one({"_id": ObjectId(id_str)})
    if not doc:
        raise HTTPException(status_code=404, detail=f"{collection} not found")
    return doc


@app.post("/api/loans")
def create_loan(payload: LoanIn):
    book = _get_by_id("book", payload.book_id)
    if book.get("copies_available", 0) <= 0:
        raise HTTPException(status_code=400, detail="No copies available")

    member = _get_by_id("member", payload.member_id)
    # create loan record
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=payload.days)
    loan_data = {
        "book_id": payload.book_id,
        "member_id": payload.member_id,
        "loan_date": now,
        "due_date": due.date().isoformat(),
        "status": "borrowed",
    }
    loan_id = create_document("loan", loan_data)

    # decrement copies_available
    db["book"].update_one({"_id": book["_id"]}, {"$inc": {"copies_available": -1}})

    return {"id": loan_id}


@app.post("/api/loans/{loan_id}/return")
def return_book(loan_id: str):
    loan = _get_by_id("loan", loan_id)
    if loan.get("status") == "returned":
        raise HTTPException(status_code=400, detail="Already returned")

    # mark returned
    now = datetime.now(timezone.utc)
    db["loan"].update_one({"_id": loan["_id"]}, {"$set": {"status": "returned", "return_date": now}})

    # increment copies_available on book
    book_id = loan.get("book_id")
    if ObjectId.is_valid(book_id):
        db["book"].update_one({"_id": ObjectId(book_id)}, {"$inc": {"copies_available": 1}})

    return {"status": "ok"}


@app.get("/api/loans")
def list_loans(status: Optional[str] = None):
    filter_dict = {}
    if status:
        filter_dict["status"] = status
    loans = get_documents("loan", filter_dict)
    for l in loans:
        l["_id"] = str(l.get("_id"))
    return loans


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
