from pydantic import BaseModel, ConfigDict, EmailStr

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True) # Bisa terima object ORM langsung

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
