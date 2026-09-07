from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # bisa terima objek ORM langsung

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
