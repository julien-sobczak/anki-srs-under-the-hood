"""
Basic implementation of SM-0 for educational purposes.

See the original paper http://super-memory.com/articles/paper.htm
"""
import random
from datetime import date, timedelta
from queue import Queue

TABLE_REPETITION_INTERVALS = [4] # First review after 4 days

# Use the factor 1.7 to determine next intervals
# Ex: 4, 7, 12, 20, ...
for i in range(1, 15):
    prev = TABLE_REPETITION_INTERVALS[i - 1]
    next = int(prev * 1.7)
    TABLE_REPETITION_INTERVALS.append(next)

DATABOOK = []
SCHEDULE_BOOK = {}

def review_question(question, repetitions):
    # Increase the chance of success with the increased number of repetitions
    return random.choice([True] * repetitions * 5 + [False])

class Page:

    def __init__(self, questions, answers):
        self.questions = questions
        self.answers = answers
        self.repetition_scores = []
        [self.repetition_scores.append([0] * 100) for q in self.questions]
        self.repetitions = []

    def review(self, day):
        remaining_questions = Queue()
        for question in self.questions:
            remaining_questions.put(question)
        repetition_score_index = len(self.repetitions)

        # Review until there is no more cards wrongly answered
        iteration = 1
        # Memorize the number of wrong answers during the first iteration
        U = 0
        while not remaining_questions.empty():

            questions_to_review = []
            while not remaining_questions.empty():
                questions_to_review.append(remaining_questions.get())

            for question in questions_to_review:
                if not review_question(question, iteration):
                    # Review again
                    remaining_questions.put(question)

                    # Add a dot in the "Repetition scores" column for the given question and session
                    self.repetition_scores[self.questions.index(question)][repetition_score_index] += 1

                    # Save the U value for the U column
                    if iteration == 1:
                        U += 1
            iteration += 1

        self.repetitions.append({
            "No": len(self.repetitions) + 1,
            "Dat": day,
            "U": U,
        })

    def print(self):
        print(f"+----------+----------+------------------------+----------------------+")
        print(f"| Question | Answer   | Repetition             | Repetitions          |")
        print(f"| field    | field    | scores                 |                      |")
        print(f"|          |          +------------------------+----------------------+")
        print(f"|          |          |  1 |  2 |  3 |  4 |  5 | No | Dat        |  U |")
        print(f"+----------+----------+----+----+----+----+----+----------------------+")
        for i, question in enumerate(self.questions):
            answer = self.answers[i]
            repetition_score1 = self.repetition_scores[i][0]
            repetition_score2 = self.repetition_scores[i][1]
            repetition_score3 = self.repetition_scores[i][2]
            repetition_score4 = self.repetition_scores[i][3]
            repetition_score5 = self.repetition_scores[i][4]

            repetition_number = i + 1
            repetition_date = ""
            repetition_U = ""
            if len(self.repetitions) > i:
                repetition_date = self.repetitions[i]["Dat"]
                repetition_U = self.repetitions[i]["U"]

            print(f"| {question:>8} | {answer:>8} | {repetition_score1:>2} | {repetition_score2:>2} | {repetition_score3:>2} | {repetition_score4:>2} | {repetition_score5:>2} | {repetition_number:>2} | {repetition_date:>10} | {repetition_U:>2} |")
            print(f"+----------+----------+------------------------+----------------------+")


if __name__ == "__main__":
    # Add a new page
    DATABOOK.append(Page(
        questions=["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10"],
        answers=["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10"],
    ))
    page_number = len(DATABOOK) - 1

    # Mark the page to review according the table of repetition intervals
    now = date.today()
    for interval in TABLE_REPETITION_INTERVALS:
        review_date = str(now + timedelta(days=interval))
        if review_date not in SCHEDULE_BOOK:
            SCHEDULE_BOOK[review_date] = []
        print(f"Page {page_number} to review on {review_date}")
        SCHEDULE_BOOK[review_date] = [page_number]

    # Review one year
    for i in range(365):
        day = str(now + timedelta(days=i))
        if not day in SCHEDULE_BOOK:
            # Nothing to review today
            continue
        # Review each planned pages
        for page in SCHEDULE_BOOK[day]:
            print(f"Reviewing page {page} on {day}")
            DATABOOK[page].review(day)

    DATABOOK[0].print()
