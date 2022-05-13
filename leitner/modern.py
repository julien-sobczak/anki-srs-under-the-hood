"""
Modern version of the Leitner System.

We use 3 boxes. Each box is reviewed at a different interval:

* Box 1: every day
* Box 2: every 2-3 days (ex: Tuesday & Friday)
* Box 3: every week (ex: Sunday)
"""
from queue import Queue
import random
from datetime import datetime, timedelta

A = 0
B = 1
C = 2
SYSTEM = [
    Queue(), # Box A
    Queue(), # Box B
    Queue(), # Box C
]


def add(card, i):
    """Add a new card in the Leitner system."""
    SYSTEM[i].put(card)

def review(card):
    """Answer a single card."""
    return random.choice([True, True, True, False])

def study_box(number):
    """Review all cards in a box."""
    cards_to_review = []
    while not SYSTEM[number].empty():
        cards_to_review.append(SYSTEM[number].get())

    for card in cards_to_review:
        answer = review(card)
        new_number = None
        if answer and number < C:
            # Promote
            new_number = number + 1
        elif not answer and number > A:
            # Demote
            new_number = number - 1
        else:
            # Replace in the same box
            new_number = number
        add(card, new_number)

def study(day):
    """Study the box according the week day."""
    weekday = day.weekday()
    if weekday == 0: # Monday
        study_box(A)
    elif weekday == 1: # Tuesday
        study_box(A)
        study_box(B)
    elif weekday == 2: # Wednesday
        study_box(A)
    elif weekday == 3: # Thursday
        study_box(A)
    elif weekday == 4: # Friday
        study_box(A)
        study_box(B)
    elif weekday == 5: # Saturday
        study_box(A)
    elif weekday == 6: # Sunday
        study_box(A)
        study_box(C)


def print_box():
    s1, s2, s3 = SYSTEM[A].qsize(), SYSTEM[B].qsize(), SYSTEM[C].qsize()
    print()
    print(f"  +-----+    +-----+    +-----+")
    print(f"  |\\ {s1:3} \\   |\\ {s2:3} \\   |\\ {s3:3} \\")
    print(f"  | +-----+  | +-----+  | +-----+")
    print(f"  | |     |  | |     |  | |     |")
    print(f"   \\|_____|   \\|_____|   \\|_____|")
    print()


if __name__ == "__main__":

    # Populate the box
    for i in range(140):
        add("New Card", 0)

        # Print study progression
        if i % 10 == 0:
            print_box()

    # Study (over 10 days)
    for i in range(10):
        day = datetime.today() - timedelta(days=10 - i)
        study(day)
        print("\n-----------------------------------\n")
        print_box()

