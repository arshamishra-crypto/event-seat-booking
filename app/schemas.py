from datetime import date, datetime
from typing import List

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Event schemas ----------

class EventCreate(BaseModel):
    name: str
    event_date: date
    rows_count: int
    seats_per_row: int


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    event_date: date
    rows_count: int
    seats_per_row: int


# ---------- Seat schemas ----------

class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_label: str
    seat_number: int
    label: str
    is_blocked: bool
    status: str  # "available" | "booked" | "blocked"


class SeatMapOut(BaseModel):
    event: EventOut
    seats: List[SeatOut]


# ---------- Booking schemas ----------

class BookingCreate(BaseModel):
    seat_ids: List[int]
    booker_name: str
    booker_email: EmailStr


class BookingOut(BaseModel):
    booking_ref: str
    seat_labels: List[str]
    booker_name: str
    booker_email: EmailStr
    created_at: datetime