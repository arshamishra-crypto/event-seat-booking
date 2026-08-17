# Admin blocking feature deployed
# admin blocking feature
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models, schemas
from .database import engine, get_db, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Event Seat Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Seat booking API is running"}
@app.post("/events", response_model=schemas.EventOut, status_code=201)
def create_event(payload: schemas.EventCreate, db: Session = Depends(get_db)):
    event = models.Event(
        name=payload.name,
        event_date=payload.event_date,
        rows_count=payload.rows_count,
        seats_per_row=payload.seats_per_row,
    )
    db.add(event)
    db.flush()

    row_letters = [chr(ord("A") + i) for i in range(payload.rows_count)]
    for row_label in row_letters:
        for seat_number in range(1, payload.seats_per_row + 1):
            db.add(models.Seat(
                event_id=event.id,
                row_label=row_label,
                seat_number=seat_number,
                label=f"{row_label}{seat_number}",
            ))

    db.commit()
    db.refresh(event)
    return event
@app.get("/events/{event_id}/seats", response_model=schemas.SeatMapOut)
def get_seat_map(event_id: int, db: Session = Depends(get_db)):
    event = db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    seats = db.query(models.Seat).filter(models.Seat.event_id == event_id).all()

    seat_out = []
    for seat in seats:
        if seat.is_blocked:
            status = "blocked"
        elif seat.booking is not None:
            status = "booked"
        else:
            status = "available"
        seat_out.append(schemas.SeatOut(
            id=seat.id,
            row_label=seat.row_label,
            seat_number=seat.seat_number,
            label=seat.label,
            is_blocked=seat.is_blocked,
            status=status,
        ))

    return schemas.SeatMapOut(event=event, seats=seat_out)

@app.patch("/seats/{seat_id}/block")
def block_seat(seat_id: int, db: Session = Depends(get_db)):
    seat = db.get(models.Seat, seat_id)
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    if seat.booking is not None:
        raise HTTPException(status_code=400, detail="Cannot block a seat that is already booked")
    seat.is_blocked = True
    db.commit()
    return {"status": "ok", "message": f"Seat {seat.label} blocked"}


@app.patch("/seats/{seat_id}/unblock")
def unblock_seat(seat_id: int, db: Session = Depends(get_db)):
    seat = db.get(models.Seat, seat_id)
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")
    seat.is_blocked = False
    db.commit()
    return {"status": "ok", "message": f"Seat {seat.label} unblocked"}

@app.post("/events/{event_id}/bookings", response_model=schemas.BookingOut, status_code=201)
def create_booking(event_id: int, payload: schemas.BookingCreate, db: Session = Depends(get_db)):
    if not payload.seat_ids:
        raise HTTPException(status_code=400, detail="seat_ids must not be empty")

    event = db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    seats = db.query(models.Seat).filter(
        models.Seat.id.in_(payload.seat_ids),
        models.Seat.event_id == event_id,
    ).all()

    if len(seats) != len(set(payload.seat_ids)):
        raise HTTPException(status_code=400, detail="One or more seat_ids are invalid for this event")

    blocked_labels = [s.label for s in seats if s.is_blocked]
    if blocked_labels:
        raise HTTPException(
            status_code=409,
            detail=f"Seat(s) unavailable: {', '.join(blocked_labels)}",
        )

    booking_ref = str(uuid.uuid4())

    try:
        for seat in seats:
            db.add(models.Booking(
                seat_id=seat.id,
                booking_ref=booking_ref,
                booker_name=payload.booker_name,
                booker_email=payload.booker_email,
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="One or more selected seats were just booked by someone else. Please choose different seats.",
        )

    return schemas.BookingOut(
        booking_ref=booking_ref,
        seat_labels=[s.label for s in seats],
        booker_name=payload.booker_name,
        booker_email=payload.booker_email,
        created_at=datetime.now(timezone.utc),
    )