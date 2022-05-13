"""
Basic implementation of SM-2 for educational purposes.

See the original paper http://super-memory.com/english/ol/sm2.htm
"""
import random
from datetime import date, timedelta
from queue import Queue

def grade(question, repetitions):
    # Increase the chance of success with the increased number of repetitions
    choices = [0] * 1 * repetitions + [1] * 2 * repetitions + [2] * 3 * repetitions + [3] * 4 * repetitions + [4] * 5 * repetitions + [5] * 6 * repetitions
    return random.choice(choices)

# Settings
I1 = 1
I2 = 6
MIN_EF = 1.3

class Item:

    def __init__(self, question, answer):
        self.question = question
        self.answer = answer
        self.EF = 2.5
        self.I = I1
        self.next_review = date.today() + timedelta(days=self.I)
        self.repetitions = 0

    def review(self, day, q):
        self.EF = max(self.EF+(0.1-(5-q)*(0.08+(5-q)*0.02)), MIN_EF)
        if q < 3:
            self.I = I1
        elif self.I == I1:
            self.I = I2
        else:
            self.I = round(self.I * self.EF)
        self.next_review = day + timedelta(days=self.I)
        self.repetitions += 1

def print_items(items):
    print(f"+----------+----------+------+-----+-------------+")
    print(f"| Question | Answer   |  EF  | I   | Next Review |")
    print(f"+----------+----------+------+-----+-------------+")
    for item in items:
        print(f"| {item.question:>8} | {item.answer:>8} | {item.EF:>.2f} | {item.I:>3} |  {item.next_review} |")
        print(f"+----------+----------+------+-----+-------------+")

if __name__ == "__main__":
    # Populate items
    items = []
    for i in range(1, 100):
        items.append(Item(f"Q{i}", f"A{i}"))

    # Review one year
    # for i in range(365):
    for i in range(365):
        day = date.today() + timedelta(days=i)
        for item in items:
            if item.next_review == day:
                q = grade(item.question, item.repetitions + 1)
                item.review(day, q)

    # Show results
    print_items(items)
