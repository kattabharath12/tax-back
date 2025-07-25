from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
import os
import json
from database import SessionLocal
from models import Document, TaxSubmission
from auth.routes import get_current_user
from .ocr import extract_document_data  # Real OCR instead of mock
from tax_engine.mapping import map_document_to_form1040

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_id = str(uuid4())
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save uploaded file
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Extract data using real OCR
    extracted_data = extract_document_data(file_path, file.content_type)
    
    # Save document to database
    doc = Document(
        id=file_id,
        user_email=current_user.email,
        filename=file.filename,
        file_path=file_path,
        content_type=file.content_type,
        document_type=extracted_data.get("document_type", "Unknown"),
        extracted_data=json.dumps(extracted_data)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Map extracted data to Form 1040 fields and auto-populate draft
    auto_fields = map_document_to_form1040(extracted_data)
    
    if auto_fields:  # Only create/update draft if we have mappable data
        # Check if user already has a draft tax submission
        draft = db.query(TaxSubmission).filter(
            TaxSubmission.user_email == current_user.email,
            TaxSubmission.status == "draft"
        ).first()

        if draft:
            # Merge new data with existing draft
            existing_data = json.loads(draft.form_data) if draft.form_data else {}
            merged_data = {**existing_data, **auto_fields}
            draft.form_data = json.dumps(merged_data)
        else:
            # Create new draft submission
            draft = TaxSubmission(
                id=str(uuid4()),
                user_email=current_user.email,
                form_data=json.dumps(auto_fields),
                status="draft"
            )
            db.add(draft)
        
        db.commit()

    return {
        "id": doc.id,
        "filename": doc.filename,
        "extracted_data": extracted_data,
        "uploaded_at": doc.uploaded_at,
        "auto_populated_fields": auto_fields if auto_fields else None
    }

@router.get("/")
def list_files(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.user_email == current_user.email).all()
    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "document_type": d.document_type,
                "extracted_data": json.loads(d.extracted_data) if d.extracted_data else None,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
            } for d in docs
        ]
    }

@router.get("/user-documents")
async def get_user_documents(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for the current user"""
    try:
        docs = db.query(Document).filter(Document.user_email == current_user.email).all()
        
        documents = []
        for doc in docs:
            doc_data = {
                "id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "upload_date": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "extracted_data": json.loads(doc.extracted_data) if doc.extracted_data else None
            }
            documents.append(doc_data)
        
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.get("/download/{document_id}")
async def download_file(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a specific document"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_email == current_user.email
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"download_url": f"/uploads/{doc.filename}", "filename": doc.filename}

@router.get("/extracted-data/{document_id}")
async def get_extracted_data(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get extracted data for a specific document"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_email == current_user.email
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    extracted_data = json.loads(doc.extracted_data) if doc.extracted_data else {}
    
    return {
        "document_id": doc.id,
        "document_type": doc.document_type,
        "filename": doc.filename,
        "extracted_data": extracted_data,
        "upload_date": doc.uploaded_at.isoformat() if doc.uploaded_at else None
    }