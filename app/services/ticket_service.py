from datetime import datetime , timezone
from decimal import Decimal
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.parking_ticket import ParkingTicket
from app.models.parking_slot import ParkingSlot
from app.models.parking_lot import ParkingLot
from app.models.vehicle import Vehicle
from app.models.driver import Driver



def generate_ticket_number() -> str:
    return f"TKT-{uuid.uuid4().hex[:8].upper()}"

def normalize_slot_size_for_vehicle(vehicle_type: str) -> str:
    """
    Map vehicle_type -> required slot_size
    """
    if not vehicle_type:
        return "standard"
    vt = vehicle_type.strip().lower()
    if vt in {"large", "suv"}:
        return "large"
    if vt in {"small"}:
        return "compact"
    return "standard"

def slot_size_is_compatible(slot_size: str, required: str) -> bool:
    """
    Compatibility rule:
      - 'large' slots fit everything
      - 'standard' fits medium/small (not large)
      - 'compact' fits small only
    """
    s = (slot_size or "standard").lower()
    if required == "large":
        return s == "large"
    if required == "standard":
        return s in {"standard", "large"}
    if required == "compact":
        return s in {"compact", "standard", "large"}
    return True


def select_best_slot(
    db: Session,
    lot_id: int,
    driver_is_handicap: bool,
    required_slot_size: str,
) -> ParkingSlot | None:
    """
    Pick the best available :
      - handicap drivers first: use handicap-accessible & closest to exit
      - non-handicap drivers: avoid handicap slots when possible
      - slot-size compatibility
    """
    # Base query: free slots in this lot
    base_q = db.query(ParkingSlot).filter(
        ParkingSlot.lot_id == lot_id,
        ParkingSlot.is_occupied == False,  # available
    )

    def ordered(q, prefer_handicap: bool):
        # order by distance_from_exit (NULLs last) for better UX
        # NOTE: If your DB is PostgreSQL, NULLS LAST works via ordering trick; here we emulate by coalescing to large number.
        return q.order_by((ParkingSlot.distance_from_exit.is_(None)).desc(),
                          ParkingSlot.distance_from_exit.asc())

    #  If driver is handicap: prefer handicap slots first
    if driver_is_handicap:
        q1 = base_q.filter(ParkingSlot.is_handicap_accessible == True)
        candidates = [s for s in ordered(q1, True).all() if slot_size_is_compatible(s.slot_size, required_slot_size)]
        if candidates:
            return candidates[0]
        # Fallback: any free slot (closest)
        q2 = base_q
        candidates = [s for s in ordered(q2, False).all() if slot_size_is_compatible(s.slot_size, required_slot_size)]
        return candidates[0] if candidates else None

    # Non-handicap: avoid handicap-accessible to keep them free
    q1 = base_q.filter(ParkingSlot.is_handicap_accessible == False)
    candidates = [s for s in ordered(q1, False).all() if slot_size_is_compatible(s.slot_size, required_slot_size)]
    if candidates:
        return candidates[0]
    # Fallback: take a handicap slot if nothing else is available
    q2 = base_q
    candidates = [s for s in ordered(q2, False).all() if slot_size_is_compatible(s.slot_size, required_slot_size)]
    return candidates[0] if candidates else None


def bump_lot_counters_on_allocate(db: Session, lot_id: int):
    lot = db.query(ParkingLot).filter(ParkingLot.id == lot_id).first()
    if lot:
        # defensive clamp
        if lot.available_slots is None:
            lot.available_slots = 0
        if lot.available_slots > 0:
            lot.available_slots -= 1
        lot.is_full = lot.available_slots == 0
        db.add(lot)

def bump_lot_counters_on_free(db: Session, lot_id: int):
    lot = db.query(ParkingLot).filter(ParkingLot.id == lot_id).first()
    if lot:
        if lot.available_slots is None:
            lot.available_slots = 0
        lot.available_slots += 1
        lot.is_full = False
        db.add(lot)


def calculate_fee(
    entry_time: datetime,
    exit_time: datetime,
    rate_per_hour: Decimal = Decimal("10.00"),
    round_up_to_hour: bool = True,
    min_fee: Decimal | None = None,
) -> Decimal:
    """
    Calculate parking fee.
    - Default: 10 per hour, rounded up to next hour.
    - min_fee: enforce a minimum if provided
    """
    seconds = (exit_time - entry_time).total_seconds()
    hours = Decimal(seconds) / Decimal(3600)
    if round_up_to_hour:
        # ceil to next 0.01 hour first, then to integer hours
        hours = (hours.quantize(Decimal("0.01"))).to_integral_value(rounding="ROUND_UP")
    fee = (hours * rate_per_hour).quantize(Decimal("0.01"))
    if min_fee is not None and fee < min_fee:
        fee = min_fee
    return fee



def allocate_ticket(
    db: Session,
    driver_id: int,
    vehicle_id: int,
    lot_id: int,
    attendant_id: int | None = None,
) -> ParkingTicket:
    """
    Allocate a slot and create a parking ticket.
    Rules:
      - One active ticket per vehicle (prevent duplicates)
      - Handicap drivers get priority on handicap slots nearest to exit
      - Slot-size compatibility
      - Mark slot occupied, decrement lot.available_slots, set is_full
    """
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    # Optional: ensure the vehicle belongs to the driver 
    if vehicle.owner_id and vehicle.owner_id != driver.id:
        raise HTTPException(status_code=400, detail="Vehicle does not belong to this driver")

    # Prevent multiple active tickets for the same vehicle
    existing = db.query(ParkingTicket).filter(
        ParkingTicket.vehicle_id == vehicle_id,
        ParkingTicket.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This vehicle already has an active ticket")

    required_slot_size = normalize_slot_size_for_vehicle(vehicle.vehicle_type)
    slot = select_best_slot(
        db=db,
        lot_id=lot_id,
        driver_is_handicap=bool(driver.is_handicap),
        required_slot_size=required_slot_size,
    )
    if not slot:
        raise HTTPException(status_code=400, detail="No available slots in this lot")

    # Mark slot as occupied and create ticket atomically
    try:
        slot.is_occupied = True
        db.add(slot)

        ticket = ParkingTicket(
            ticket_number=generate_ticket_number(),
            vehicle_id=vehicle.id,
            driver_id=driver.id,
            lot_id=lot_id,
            slot_id=slot.id,
            entry_time=datetime.now(timezone.utc),
            payment_status="pending",
            is_active=True,
            attendant_id=attendant_id,
            # Make sure parking_fee is properly handled if set
            parking_fee=Decimal('0.00') if hasattr(ParkingTicket, 'parking_fee') else None
        )
        db.add(ticket)

        bump_lot_counters_on_allocate(db, lot_id)

        db.commit()
        db.refresh(ticket)
        return ticket
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to allocate ticket")



def close_ticket(
    db: Session,
    ticket_id: int,
    mark_paid: bool = False,
    rate_per_hour: Decimal = Decimal("10.00"),
    min_fee: Decimal | None = None,
) -> ParkingTicket:
    """Close a ticket and calculate parking fee"""
    ticket = db.query(ParkingTicket).filter(
        ParkingTicket.id == ticket_id,
        ParkingTicket.is_active == True
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Active ticket not found")

    # ✅ FIXED: Remove extra parentheses
    ticket.exit_time = datetime.now(timezone.utc)
    ticket.parking_fee = calculate_fee(
        ticket.entry_time, 
        ticket.exit_time, 
        rate_per_hour=rate_per_hour, 
        min_fee=min_fee
    )
    ticket.is_active = False
    if mark_paid:
        ticket.payment_status = "paid"

    # Free the slot
    if ticket.slot_id:
        slot = db.query(ParkingSlot).filter(ParkingSlot.id == ticket.slot_id).first()
        if slot:
            slot.is_occupied = False
            db.add(slot)

    bump_lot_counters_on_free(db, ticket.lot_id)

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket(db: Session, ticket_id: int) -> ParkingTicket:
    """Get ticket by ID"""
    ticket = db.query(ParkingTicket).filter(ParkingTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

def list_active_tickets(
    db: Session, 
    lot_id: int | None = None, 
    driver_id: int | None = None, 
    vehicle_id: int | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[ParkingTicket]:
    """List active tickets with optional filtering"""
    q = db.query(ParkingTicket).filter(ParkingTicket.is_active == True)
    if lot_id:
        q = q.filter(ParkingTicket.lot_id == lot_id)
    if driver_id:
        q = q.filter(ParkingTicket.driver_id == driver_id)
    if vehicle_id:
        q = q.filter(ParkingTicket.vehicle_id == vehicle_id)
    return q.offset(offset).limit(limit).all()

def list_ticket_history(
    db: Session, 
    lot_id: int | None = None, 
    driver_id: int | None = None, 
    vehicle_id: int | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[ParkingTicket]:
    """List ticket history with optional filtering"""
    q = db.query(ParkingTicket).filter(ParkingTicket.is_active == False)
    if lot_id:
        q = q.filter(ParkingTicket.lot_id == lot_id)
    if driver_id:
        q = q.filter(ParkingTicket.driver_id == driver_id)
    if vehicle_id:
        q = q.filter(ParkingTicket.vehicle_id == vehicle_id)
    return q.offset(offset).limit(limit).order_by(ParkingTicket.exit_time.desc()).all()
