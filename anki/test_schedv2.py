# coding: utf-8

import time
import copy
import unittest
import copy
from pprint import pprint

from schedv2 import Collection, Note, intTime, STARTING_FACTOR, deckDefaultConf

# Tests are similar to Anki test suite.
# They have been slightly adapted to remove unsupported features
# and use unittest as other tests in this repository.


def checkRevIvl(d, c, targetIvl):
    """Checks the current interval in between an acceptable range."""
    min, max = d.sched._fuzzIvlRange(targetIvl)
    return min <= c.ivl <= max


class TestScheduler(unittest.TestCase):


    def test_basics(self):
        d = Collection()
        assert not d.sched.getCard()


    def test_new(self):
        d = Collection()
        # add a note
        f = Note()
        f['Front'] = "one"; f['Back'] = "two"
        d.addNote(f)
        # fetch it
        c = d.sched.getCard()
        assert c
        assert c.queue == 0
        assert c.type == 0
        # if we answer it, it should become a learn card
        t = intTime()
        d.sched.answerCard(c, 1)
        assert c.queue == 1
        assert c.type == 1
        assert c.due >= t


    @unittest.skip("slow test")
    def test_newLimits(self):
        d = Collection()
        # Lower the new cards per day limit
        deckConf = copy.deepcopy(deckDefaultConf)
        deckConf['new']['perDay'] = 2
        d.deckConf = deckConf
        # add some notes
        for i in range(3):
            f = Note()
            f['Front'] = str(i)
            f['Back'] = str(i)
            d.addNote(f)
        # Force the fill of the new queue
        d.sched._fillNew()
        # Ensure limit is satisfied
        assert len(d.sched._newQueue) == 2


    def test_learn(self):
        d = Collection()
        # add a note
        f = Note()
        f['Front'] = "one"; f['Back'] = "two"
        f = d.addNote(f)
        # set as a learn card and rebuild queues
        c = d.cards[0]
        c.queue = 0
        c.type = 0
        # sched.getCard should return it, since it's due in the past
        c = d.sched.getCard()
        assert c
        deckConf = copy.deepcopy(deckDefaultConf)
        deckConf['new']['delays'] = [0.5, 3, 10]
        d.deckConf = deckConf
        # fail it
        d.sched.answerCard(c, 1)
        # it should have three reps left to graduation
        assert c.left%1000 == 3
        assert c.left//1000 == 3
        # it should by due in 30 seconds
        t = round(c.due - time.time())
        assert t >= 25 and t <= 40
        # pass it once
        d.sched.answerCard(c, 3)
        # it should by due in 3 minutes
        dueIn = c.due - time.time()
        assert 179 <= dueIn <= 180*1.25
        assert c.left%1000 == 2
        assert c.left//1000 == 2
        # pass again
        d.sched.answerCard(c, 3)
        # it should by due in 10 minutes
        dueIn = c.due - time.time()
        assert 599 <= dueIn <= 600*1.25
        assert c.left%1000 == 1
        assert c.left//1000 == 1
        # the next pass should graduate the card
        assert c.queue == 1
        assert c.type == 1
        d.sched.answerCard(c, 3)
        assert c.queue == 2
        assert c.type == 2
        # should be due tomorrow, with an interval of 1
        assert c.due == d.sched.today+1
        assert c.ivl == 1
        # or normal removal
        c.type = 0
        c.queue = 1
        d.sched.answerCard(c, 4)
        assert c.type == 2
        assert c.queue == 2
        assert checkRevIvl(d, c, 4)


    def test_relearn(self):
        d = Collection()
        f = Note()
        f['Front'] = "one"
        d.addNote(f)
        c = d.cards[0]
        c.ivl = 100
        c.due = d.sched.today
        c.type = c.queue = 2

        # fail the card
        c = d.sched.getCard()
        d.sched.answerCard(c, 1)
        assert c.queue == 1
        assert c.type == 3
        assert c.ivl == 1

        # immediately graduate it
        d.sched.answerCard(c, 4)
        assert c.queue == c.type == 2
        assert c.ivl == 1
        assert c.due == d.sched.today + c.ivl


    def test_learn_day(self):
        d = Collection()
        # add a note
        f = Note()
        f['Front'] = "one"
        f = d.addNote(f)
        c = d.sched.getCard()
        deckConf = copy.deepcopy(deckDefaultConf)
        deckConf['new']['delays'] = [1, 10, 1440, 2880]
        d.deckConf = deckConf
        # pass it
        d.sched.answerCard(c, 3)
        # two reps to graduate, 1 more today
        assert c.left%1000 == 3
        assert c.left//1000 == 1
        c = d.sched.getCard()
        assert d.sched.nextIvl(c, 3) == 86400
        # answering it will place it in queue 3
        d.sched.answerCard(c, 3)
        assert c.due == d.sched.today+1
        assert c.queue == 3
        assert not d.sched.getCard()
        # for testing, move it back a day
        c.due -= 1
        c = d.sched.getCard()
        # nextIvl should work
        assert d.sched.nextIvl(c, 3) == 86400*2
        # if we fail it, it should be back in the correct queue
        d.sched.answerCard(c, 1)
        assert c.queue == 1
        c = d.sched.getCard()
        d.sched.answerCard(c, 3)
        # simulate the passing of another two days
        c.due -= 2
        # the last pass should graduate it into a review card
        assert d.sched.nextIvl(c, 3) == 86400
        d.sched.answerCard(c, 4)
        assert c.queue == c.type == 2
        # if the lapse step is tomorrow, failing it should handle the counts
        # correctly
        c.due = 0
        d.deckConf['lapse']['delays'] = [1440]
        c = d.sched.getCard()
        d.sched.answerCard(c, 1)
        assert c.queue == 3


    def test_reviews(self):
        d = Collection()
        # add a note
        f = Note()
        f['Front'] = "one"; f['Back'] = "two"
        d.addNote(f)
        # set the card up as a review card, due 8 days ago
        c = d.cards[0]
        c.type = 2
        c.queue = 2
        c.due = d.sched.today - 8
        c.ivl = 100
        c.factor = STARTING_FACTOR
        c.reps = 3
        c.lapses = 1
        # try with an ease of 2
        ##################################################
        d.sched.answerCard(c, 2)
        assert c.queue == 2
        # the new interval should be (100) * 1.2 = 120
        assert checkRevIvl(d, c, 120)
        assert c.due == d.sched.today + c.ivl
        # factor should have been decremented
        assert c.factor == 2350
        # check counters
        assert c.lapses == 1
        assert c.reps == 4
        # ease 3
        ##################################################
        # reset settings
        c.due = d.sched.today - 8
        c.ivl = 100
        c.factor = STARTING_FACTOR
        d.sched.answerCard(c, 3)
        # the new intervcal should be (100 + 8/2) * 2.5 = 260
        assert checkRevIvl(d, c, 260)
        assert c.due == d.sched.today + c.ivl
        # factor should have been left alone
        assert c.factor == STARTING_FACTOR
        # ease 4
        ##################################################
        # reset settings
        c.due = d.sched.today - 8
        c.ivl = 100
        c.factor = STARTING_FACTOR
        d.sched.answerCard(c, 4)
        # the new interval should be (100 + 8) * 2.5 * 1.3 = 351
        assert checkRevIvl(d, c, 351)
        assert c.due == d.sched.today + c.ivl
        # factor should have been increased
        assert c.factor == 2650
        # leech handling
        ##################################################
        # reset settings
        c.due = d.sched.today - 8
        c.ivl = 100
        c.factor = STARTING_FACTOR
        c.lapses = 7
        d.sched.answerCard(c, 1)
        assert "leech" in c.note.tags
        assert c.queue == -1
        assert c.ivl == 1


if __name__ == '__main__':
    unittest.main()
