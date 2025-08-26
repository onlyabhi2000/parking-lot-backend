from pydantic import BaseModel
# from typing import Optional

class VehicleCreate(BaseModel):
    plate_number: str
    make: str
    model: str | None = None
    color: str
    vehicle_type: str
    owner_id: int

class VehicleOut(BaseModel):
    id: int
    plate_number: str
    make: str
    model: str | None = None
    color: str
    vehicle_type: str
    owner_id: int | None = None

    class Config:
        from_attributes = True

## schema for the search -filter
class VehicleSearch(BaseModel):
    make: str | None = None
    model: str | None = None
    color: str | None = None
    vehicle_type: str | None = None

    class Config:
        from_attributes = True
