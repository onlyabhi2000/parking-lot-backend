from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.attendant import Attendant
from app.schemas.attendant import AttendantCreate
from app.core.security import hash_password

class AttendantService:
    @staticmethod
    def create_attendant(db: Session, attendant_data: AttendantCreate) -> Attendant:
        try:
            # Hash the password
            hashed_password = hash_password(attendant_data.password)
            
            # Create new attendant
            db_attendant = Attendant(
                name=attendant_data.name,
                phone=attendant_data.phone,
                employee_id=attendant_data.employee_id,
                email=attendant_data.email,
                password=hashed_password,
                is_active=attendant_data.is_active
            )
            
            db.add(db_attendant)
            db.commit()
            db.refresh(db_attendant)
            return db_attendant
            
        except IntegrityError as e:
            db.rollback()
            # Check which constraint failed
            if "phone" in str(e.orig):
                raise ValueError("Phone number already exists")
            elif "employee_id" in str(e.orig):
                raise ValueError("Employee ID already exists")
            elif "email" in str(e.orig):
                raise ValueError("Email already exists")
            else:
                raise ValueError("Duplicate entry found")
        except Exception as e:
            db.rollback()
            raise
    
    @staticmethod
    def delete_attendant(db: Session, attendant_id: int) -> bool:
        db_attendant = db.query(Attendant).filter(Attendant.id == attendant_id).first()
        
        if not db_attendant:
            return False
        
        db.delete(db_attendant)
        db.commit()
        return True
    
    @staticmethod
    def get_attendant_by_id(db: Session, attendant_id: int) -> Attendant:
        return db.query(Attendant).filter(Attendant.id == attendant_id).first()