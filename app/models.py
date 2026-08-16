from sqlalchemy import Column, Integer, String, Date, Boolean, TIMESTAMP, ForeignKey, CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    event_date = Column(Date, nullable=False)
    rows_count = Column(Integer, nullable=False)
    seats_per_row = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    seats = relationship("Seat", back_populates="event", cascade="all, delete-orphan")


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    row_label = Column(String(5), nullable=False)
    seat_number = Column(Integer, nullable=False)
    label = Column(String(10), nullable=False)
    is_blocked = Column(Boolean, nullable=False, default=False)

    event = relationship("Event", back_populates="seats")
    booking = relationship("Booking", back_populates="seat", uselist=False)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False, unique=True)
    booking_ref = Column(CHAR(36), nullable=False)
    booker_name = Column(String(255), nullable=False)
    booker_email = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    seat = relationship("Seat", back_populates="booking")