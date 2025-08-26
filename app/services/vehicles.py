from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.schemas.vehicles import VehicleCreate , VehicleOut  , VehicleSearch

def create_vehicle(db: Session, payload: VehicleCreate) -> Vehicle:
    existing = db.query(Vehicle).filter(Vehicle.plate_number == payload.plate_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vehicle plate number already registered")


    driver = db.query(Driver).filter(Driver.id == payload.owner_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Owner not found")

    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle

def get_vehicle(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


## service  code to  seach vehicle by coloe-make , vheicle type and model 
def vehicle_filter(db: Session, filters: VehicleSearch):
    query = db.query(Vehicle)

    if filters.make:
        query = query.filter(Vehicle.make.ilike(f"%{filters.make}%"))
    if filters.model:
        query = query.filter(Vehicle.model.ilike(f"%{filters.model}%"))
    if filters.color:
        query = query.filter(Vehicle.color.ilike(f"%{filters.color}%"))
    if filters.vehicle_type:
        query = query.filter(Vehicle.vehicle_type.ilike(f"%{filters.vehicle_type}%"))

    return query.all()