from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.configuration.db import get_db
from app.schemas.attendant import AttendantCreate, AttendantResponse
from app.services.attendant_service import AttendantService
from app.utils.response import standard_response

router = APIRouter(prefix="/attendants", tags=["Attendants"])

@router.post("/")
def create_attendant(
    attendant: AttendantCreate, 
    db: Session = Depends(get_db)
):
    """Create a new attendant"""
    try:
        new_attendant = AttendantService.create_attendant(db, attendant)
        attendant_data = AttendantResponse.model_validate(new_attendant)
        
        return standard_response(
            status_code=201,
            message="Attendant created successfully",
            data=attendant_data.model_dump()
        )
        
    except ValueError as e:
        return standard_response(
            status_code=400,
            message=str(e)
        )
        
    except Exception as e:
        return standard_response(
            status_code=500,
            message="Failed to create attendant"
        )

@router.delete("/{attendant_id}")
def delete_attendant(
    attendant_id: int,
    db: Session = Depends(get_db)
):
    """Delete an attendant by ID"""
    try:
        # Check if attendant exists
        attendant = AttendantService.get_attendant_by_id(db, attendant_id)
        if not attendant:
            return standard_response(
                status_code=404,
                message="Attendant not found"
            )
        
        # Delete attendant
        deleted = AttendantService.delete_attendant(db, attendant_id)
        
        if deleted:
            return standard_response(
                status_code=200,
                message="Attendant deleted successfully"
            )
        else:
            return standard_response(
                status_code=500,
                message="Failed to delete attendant"
            )
            
    except Exception as e:
        return standard_response(
            status_code=500,
            message="Failed to delete attendant"
        )