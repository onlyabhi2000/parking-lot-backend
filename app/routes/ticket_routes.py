from fastapi import APIRouter, Depends, Query ,  HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.configuration.db import get_db
from app.services import ticket_service
from app.utils.response import standard_response  # (status_code, message, data)

router = APIRouter(prefix="/tickets", tags=["Parking Tickets"])
from app.schemas.ticket import TicketListResponse , TicketClose , TicketCreate , TicketResponse




@router.post("/")
def allocate_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    """Allocate a parking ticket"""
    try:
        # Get the ticket from service
        ticket = ticket_service.allocate_ticket(
            db=db,
            driver_id=payload.driver_id,
            vehicle_id=payload.vehicle_id,
            lot_id=payload.lot_id,
            attendant_id=payload.attendant_id
        )
        
        # Convert ORM object to Pydantic model
        ticket_data = TicketResponse.model_validate(ticket)
        
        return standard_response(
            status_code=201,
            message="Ticket allocated successfully",
            data=ticket_data.model_dump()
        )
        
    except HTTPException as e:
        return standard_response(
            status_code=e.status_code,
            message=e.detail
        )
        
    except Exception as e:
        return standard_response(
            status_code=500,
            message="Failed to allocate ticket"
        )


@router.post("/{ticket_id}/close", response_model=TicketResponse)
def close_ticket(ticket_id: int, payload: TicketClose, db: Session = Depends(get_db)):
    ticket = ticket_service.close_ticket(db, ticket_id, payload.mark_paid)
    return standard_response(
        status_code=200,
        message="Ticket closed successfully",
        data=ticket
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.get_ticket(db, ticket_id)
    return standard_response(
        status_code=200,
        message="Ticket retrieved successfully",
        data=ticket
    )


@router.get("/active", response_model=TicketListResponse)
def list_active_tickets(db: Session = Depends(get_db)):
    pass
