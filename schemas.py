from pydantic import BaseModel, EmailStr


class BookingRequest(BaseModel):
    class_id: int
    client_name: str
    client_email: EmailStr



