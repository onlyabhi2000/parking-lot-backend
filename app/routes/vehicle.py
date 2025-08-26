from fastapi import APIRouter  , Depends
from app.services.vehicles import create_vehicle , get_vehicle , vehicle_filter
from sqlalchemy.orm import Session
from app.configuration.db import get_db
from app.models.vehicle import Vehicle
from app.schemas.vehicles import VehicleCreate , VehicleOut , VehicleSearch
from app.utils.response import standard_response
from app.services.vehicles import vehicle_filter

router = APIRouter(prefix = '/vehicles' , tags = ['Vehicles'])

@router.get("/search-vehicle")
def search_vehicle(
    filters: VehicleSearch = Depends(),  
    db: Session = Depends(get_db)
):
    vehicles = vehicle_filter(db, filters)
    return {
        "status_code": 200,
        "message": "Vehicles fetched successfully",
        "data": vehicles
    }

@router.post('/')
def register_vehicle(payload:VehicleCreate , db : Session = Depends(get_db)):
    vehicle = create_vehicle( db , payload)
    data = VehicleOut.model_validate(vehicle).model_dump()
    return standard_response(201 , "Vehicle registered sucessfuly" , data)

@router.get('/{vehicle_id}')
def fetch_vehicle(vehicle_id : int , db : Session = Depends(get_db)):
    vehicle = get_vehicle(db , vehicle_id)
    data = VehicleOut.model_validate(vehicle).model_dump()
    return standard_response(200 , "Vehicle fetched successfully" , data)

