# Event Seat Booking System - Backend

FastAPI backend for the Event Seat Booking System. The main challenge here was handling concurrent seat bookings safely — making sure two people can't accidentally book the same seat at the exact same time.

**Live Demo:** https://event-seat-booking-production-6b5f.up.railway.app

## Stack

- **Framework:** FastAPI (Python) — fast, easy to understand, great for building APIs
- **Database:** MySQL — solid choice for this kind of data
- **Deployment:** Railway — connects directly to GitHub, auto-deploys on push
- **ORM:** SQLAlchemy — makes working with databases in Python clean and safe

## The Race Condition Problem (and How I Solved It)

When I first thought about building this, the naive approach would be:
1. Check if a seat is available
2. Book it

But here's the issue — between steps 1 and 2, someone else could grab that same seat. This is called a **race condition**, and it's sneaky because it only happens under specific timing conditions.

### My Solution: Database-Level Atomicity

Instead of trying to prevent this at the application level (which is fragile), I let the database handle it. I use **three layers of protection:**

**1. UNIQUE Constraint** 
I made `bookings.seat_id` UNIQUE in the database. This means the database itself will reject any attempt to book the same seat twice. If two requests try to book the same seat, the database immediately rejects the second one.

**2. Single Transaction**
All the seat insertions for one booking request happen in ONE database transaction. Either ALL the seats book successfully, or NONE of them do. No partial bookings, no half-booked states.

**3. Integrity Check**
Admins can block specific seats (e.g., broken chair, reserved for accessibility). Booked seats can't be blocked. This prevents admin errors.

### Example: How It Works in Practice

The key insight: the database's UNIQUE constraint is checked at the exact moment we try to insert. There's no race window because the check and insert are atomic.

## Database Schema

I kept it simple and clean:

```sql
CREATE TABLE events (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  event_date DATE NOT NULL,
  rows_count INT NOT NULL,
  seats_per_row INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE seats (
  id INT PRIMARY KEY AUTO_INCREMENT,
  event_id INT NOT NULL,
  row_label VARCHAR(5) NOT NULL,
  seat_number INT NOT NULL,
  label VARCHAR(10) NOT NULL,
  is_blocked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE bookings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  seat_id INT NOT NULL UNIQUE,
  booking_ref VARCHAR(36) NOT NULL INDEX,
  booker_name VARCHAR(255) NOT NULL,
  booker_email VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (seat_id) REFERENCES seats(id)
);
```

**Why this design?** The `booking.seat_id` UNIQUE constraint is the core of the whole system. It guarantees that each seat can only be booked once, and the database enforces this at insertion time. No application logic needed.

## API Endpoints

### Create an Event

**POST /events**
```bash
curl -X POST https://event-seat-booking-production-6b5f.up.railway.app/events \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Taylor Swift Concert",
    "event_date": "2026-09-15",
    "rows_count": 10,
    "seats_per_row": 20
  }'
```

Returns: Event object with id

### Get Seat Map

**GET /events/{event_id}/seats**
```bash
curl https://event-seat-booking-production-6b5f.up.railway.app/events/1/seats
```

Returns: Event + all seats, each with a status (available/booked/blocked)

### Book Seats (The Important One)

**POST /events/{event_id}/bookings**
```bash
curl -X POST https://event-seat-booking-production-6b5f.up.railway.app/events/1/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "seat_ids": [1, 2, 3],
    "booker_name": "Alice",
    "booker_email": "alice@example.com"
  }'
```

Returns: `201` with booking reference on success, or `409` if any seat is taken.

This endpoint is where all the concurrency magic happens. It tries to insert bookings for all the seats at once. If ANY seat is already booked, the whole transaction fails and rolls back.

### Admin Actions

**PATCH /seats/{seat_id}/block**
```bash
curl -X PATCH https://event-seat-booking-production-6b5f.up.railway.app/seats/1/block \
  -H "Content-Type: application/json" \
  -d '{}'
```

**PATCH /seats/{seat_id}/unblock**
```bash
curl -X PATCH https://event-seat-booking-production-6b5f.up.railway.app/seats/1/unblock \
  -H "Content-Type: application/json" \
  -d '{}'
```

These let admins mark seats as unavailable without deleting them.

## Local Development

### Prerequisites
- Python 3.11+
- MySQL 8.0+
- pip

### Getting Started

1. Clone it
```bash
git clone https://github.com/arshamishra-crypto/event-seat-booking.git
cd event-seat-booking/backend
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up MySQL
```bash
sudo service mysql start  # or: brew services start mysql (macOS)
mysql -u root -p
```

Then in MySQL:
```sql
CREATE DATABASE seat_booking;
CREATE USER 'seatapp'@'localhost' IDENTIFIED BY 'seatapp_dev_pw';
GRANT ALL PRIVILEGES ON seat_booking.* TO 'seatapp'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

5. Create `.env` file

6. Run the server
```bash
python -m uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs to see all endpoints in Swagger UI.

## Testing the Concurrency Safety

I included a test that actually proves the race condition is prevented:

```bash
python race_test.py
```

This spawns two threads that try to book the same seat simultaneously. One succeeds (returns 201), and one fails with a conflict (409). If the race condition existed, both would succeed — but they don't, because the database blocks it.

## Deploying to Railway

1. Push your code to GitHub
2. Connect your GitHub repo in Railway dashboard
3. Add environment variable: `DATABASE_URL` (Railway gives you this when you create a MySQL addon)
4. Railway auto-deploys whenever you push to main

That's it. Seriously, it just works.

## Project Structure

## Why I Made These Design Choices

**Atomic Multi-Seat Booking**
Why would you let someone book 3 seats if one of them got taken by someone else right before submission? The all-or-nothing approach means the user either books all 3 or none — no weird partial states.

**UNIQUE Constraint Instead of Application Logic**
I could write code in Python to check if a seat is booked before inserting. But what if two requests check at the exact same millisecond? The database UNIQUE constraint is bulletproof because it's checked atomically.

**Single Transaction Per Booking**
All the inserts for one booking happen in one go. Either they all commit, or they all rollback. The database handles this automatically.

**Admin Blocking Feature**
Without blocking, admins would have to delete and recreate seats. With blocking, they can mark seats as unavailable without losing data.

**Stateless REST API**
No session management, no cookies. Each request has all the info it needs. Makes scaling easier and reduces bugs.

## Error Codes

- `404` — Event or seat doesn't exist
- `400` — Bad request (empty seat list, invalid IDs, etc.)
- `409` — Conflict (seat already booked or blocked)
- `500` — Unexpected error on our end

## Security

- ✅ SQLAlchemy prevents SQL injection automatically
- ✅ Database constraints prevent logical errors (no double-booking by design)
- ✅ CORS is enabled (needed for frontend)
- ⚠️ No authentication yet (this is a demo; production would have JWT tokens)

## What I'd Add Next

- User authentication (sign up, login, saved bookings)
- Booking cancellation with refund tracking
- Payment integration (Stripe, PayPal)
- Email confirmations
- WebSocket for real-time seat updates
- Rate limiting to prevent abuse
- Seat categories (VIP, standard, accessible seating)
- Analytics dashboard

---

Questions? Hit me up at arsha.mishra@gmail.com
