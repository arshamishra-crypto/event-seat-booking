import threading
import requests

SEAT_ID = 3  # an available seat from event 1

results = {}


def book(name, email, key):
    resp = requests.post(
        "http://localhost:8000/events/1/bookings",
        json={"seat_ids": [SEAT_ID], "booker_name": name, "booker_email": email},
    )
    results[key] = (resp.status_code, resp.json())


t1 = threading.Thread(target=book, args=("Sana", "sana@example.com", "request_1"))
t2 = threading.Thread(target=book, args=("Vikram", "vikram@example.com", "request_2"))

t1.start()
t2.start()
t1.join()
t2.join()

print("Request 1:", results["request_1"])
print("Request 2:", results["request_2"])

statuses = [results["request_1"][0], results["request_2"][0]]
if statuses.count(201) == 1 and statuses.count(409) == 1:
    print("\nPASS: exactly one booking succeeded, one was correctly rejected.")
else:
    print(f"\nFAIL: got statuses {statuses} — expected one 201 and one 409.")