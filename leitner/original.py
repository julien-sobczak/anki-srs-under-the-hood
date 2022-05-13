"""
Original version of the Leitner System.

We use a large physical wooden box with 5 partitions with increasing sizes (1, 2, 5, 8, and 14 cm).
The student could only review cards in a partition once it was full, moving them
in the previous or next partition based on the answer.
"""
from queue import Queue
import random

CARDS_PER_CM = 5

BOX = [
    Queue(1 * CARDS_PER_CM),
    Queue(2 * CARDS_PER_CM),
    Queue(5 * CARDS_PER_CM),
    Queue(8 * CARDS_PER_CM),
    Queue(14 * CARDS_PER_CM),
]

def add(card, i):
    BOX[i].put(card)
    if BOX[i].full():
        study()

def review(card):
    return random.choice([True, True, True, False])


def study():
    for index, partition in enumerate(BOX):
        if partition.full():
            # Time to review the cards
            print(f"Time to study partition {index + 1}!")

            cards_to_review = []
            while not partition.empty():
                cards_to_review.append(partition.get())

            for card in cards_to_review:
                answer = review(card)
                new_index = None
                if answer and index + 1 < len(BOX):
                    # Promote
                    new_index = index + 1
                elif not answer and index - 1 > 0:
                    # Demote
                    new_index = 0 # MN: The Leitner original System moves to the first partition
                else:
                    # Replace in the same partition
                    new_index = index
                add(card, new_index)

def print_box():
    s1, s2, s3, s4, s5 = BOX[0].qsize(), BOX[1].qsize(), BOX[2].qsize(), BOX[3].qsize(), BOX[4].qsize()
    print(f"  +-----+-------+----------+-------------+------------------+")
    print(f"  |\\ {s1:3} \\   {s2:3} \\      {s3:3} \\         {s4:3} \\              {s5:3} \\")
    print(f"  | +-----+-------+----------+-------------+------------------+")
    print(f"  | |                                                         |")
    print(f"   \\|_________________________________________________________|")


if __name__ == "__main__":

    # Populate the box
    for i in range(140):
        add("New Card", 0)

        if i % 10 == 0:
            print_box()

    # Study
    study()
    print_box()

