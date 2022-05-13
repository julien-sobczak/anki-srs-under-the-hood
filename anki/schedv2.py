# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time
import random
import datetime

# Whether new cards should be mixed with reviews, or shown first or last
NEW_CARDS_DISTRIBUTE = 0
NEW_CARDS_LAST = 1
NEW_CARDS_FIRST = 2

# The initial factor when card get promoted
STARTING_FACTOR = 2500


## Utils

def ids2str(ids):
    """Given a list of integers, return a string '(int1,int2,...)'."""
    return "(%s)" % ",".join(str(i) for i in ids)

def intTime(scale=1):
    "The time in integer seconds. Pass scale=1000 to get milliseconds."
    return int(time.time()*scale)

def intId():
    """Returns a unique integer identifier."""
    t = intTime(1000)
    # Make sure the next call to the function returns a different value
    while intTime(1000) == t:
        time.sleep(1)
    return t

# Default collection configuration
colDefaultConf = {
    'newSpread': NEW_CARDS_DISTRIBUTE,
    # In which order to view to review the cards:
    # - NEW_CARDS_DISTRIBUTE (Mix new cards and reviews)
    # - NEW_CARDS_LAST (see new cards after review)
    # - NEW_CARDS_FIRST (see new card before review)

    'collapseTime': 1200,
    # 'Preferences>Basic>Learn ahead limit'*60
    # If there is no more card to review now but next card in learning
    # is in less than 'collapseTime' seconds, show it now.
}

# anki/decks.py
# Default deck configuration
deckDefaultConf = {
    # The configuration for new cards:
    'new': {
        'delays': [1, 10],
        # The list of successive delays between the learning steps
        # of the new cards.

        'ints': [1, 4],
        # The list of delays according to the button pressed while leaving
        # the learning mode. Good, easy and unused.

        'initialFactor': STARTING_FACTOR,
        # The initial ease factor

        'perDay': 20,
        # Maximal number of new cards shown per day.
    },

    # The configuration for lapse cards:
    'lapse': {
        'delays': [10],
        # The list of successive delays between the learning steps
        # of the new cards.

        'mult': 0,
        # Percent by which to multiply the current interval when a card lapsed.

        'minInt': 1,
        # A lower limit to the new interval after a leech.

        'leechFails': 8,
        # The number of lapses authorized before doing leechAction.
    },

    # The configuration for review cards:
    'rev': {
        'perDay': 200,
        # Numbers of cards to review per day.

        'ease4': 1.3,
        # The number to add to the easyness when the "Easy" button is pressed.

        'fuzz': 0.05,
        # The new interval is multiplied by a random number
        # between -fuzz and fuzz.

        'ivlFct': 1,
        # Multiplication factor applied to the intervals Anki generates.

        'maxIvl': 36500,
        # The maximal interval for review.

        'hardFactor': 1.2,
        # The multiplication factor applied to the interval for cards
        # in review when pressing "Hard"
    },
}


class Collection:

    # anki/anki/collection.py
    def __init__(self, id=None):
        d = datetime.datetime.today()
        d = datetime.datetime(d.year, d.month, d.day)
        self.crt = int(time.mktime(d.timetuple()))  # Timestamp of the creation date in seconds.
        self.cards = []                             # In-memory list of cards (as we are not using a SQL database)
        self.colConf = colDefaultConf               # Configuration of the collection
        self.deckConf = deckDefaultConf             # Configuration of the deck (we consider only a single deck)
        self.sched = Scheduler(self)

    def addNote(self, note):
        "Add a note to the collection. Return number of new cards."
        # add cards
        ncards = 0
        for template in note.templates:
            self.cards.append(self._newCard(note, template))
            ncards += 1
        return ncards

    def _newCard(self, note, template):
        "Create a new card."
        card = Card(note)
        # Template is used to determine the card index among other cards
        # of the same note.
        # We don't use it as we only work with "Basic" note in this tutorial.
        return card


class Note:

    # anki/anki/notes.py
    def __init__(self, id=None):
        if id:
            self.id = id
        else:
            self.id = intId()
        self.tags = []
        # Note: We support only the "Basic" model (Front/Back)
        # These fields are dynamically initialized in Anki
        # based on the note type.
        self.fields = [""] * 2
        self._fmap = {
            'Front': (0, {'ord': 0}),
            'Back':  (1, {'ord': 1}),
        }
        self.templates = [
            {
                'name': 'Card 1',
                'afmt': '{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}',
                'qfmt': '{{Front}}',
                'ord': 0,
            }]

    def addTag(self, tag):
        if not tag in self.tags:
            self.tags.append(tag)

    # Dict interface
    ##################################################

    def keys(self):
        return list(self._fmap.keys())

    def values(self):
        return self.fields

    def items(self):
        return [(f['name'], self.fields[ord])
                for ord, f in sorted(self._fmap.values())]

    def _fieldOrd(self, key):
        try:
            return self._fmap[key][0]
        except:
            raise KeyError(key)

    def __getitem__(self, key):
        return self.fields[self._fieldOrd(key)]

    def __setitem__(self, key, value):
        self.fields[self._fieldOrd(key)] = value

    def __contains__(self, key):
        return key in list(self._fmap.keys())


class Card:
    # anki/anki/cards.py
    def __init__(self, note, id=None):
        if id:
            self.id = id
        else:
            self.id = intId()   # The epoch milliseconds of when the card was created
        self.note = note
        self.due = note.id      # The note ID is used as the due date for new cards
        self.crt = intTime()    # Timestamp of the creation date in second.
        self.type = 0           # 0=new, 1=learning, 2=review, 3=relearning
        self.queue = 0          # Queue types:
                                #   -1=suspend     => leeches as manual suspension is not supported
                                #    0=new         => new (never shown)
                                #    1=(re)lrn     => learning/relearning
                                #    2=rev         => review (as for type)
                                #    3=day (re)lrn => in learning, next review in at least a day after the previous review
        self.ivl = 0            # The interval. Negative = seconds, positive = days
        self.factor = 0         # The ease factor in permille (ex: 2500 = the interval will be multiplied by 2.5 the next time you press "Good")
        self.reps = 0           # The number of reviews
        self.lapses = 0         # The number of times the card went from a "was answered correctly" to "was answered incorrectly" state
        self.left = 0           # Of the form a*1000+b, with:
                                #   a the number of reps left today
                                #   b the number of reps left till graduation
                                # for example: '2004' means 2 reps left today and 4 reps till graduation
        self.due = self.id      # Due is used differently for different card types:
                                # - new: note id or random int
                                # - due: integer day, relative to the collection's creation time
                                # - learning: integer timestamp in second

class Scheduler:

    def __init__(self, col):
        self.col = col           # The collection used to retrieve the cards and the configuration options
        self.queueLimit = 50     # An upper limit for new cards and day relearning cards (= cards that are harder to learn)
        self.reportLimit = 1000  # An upper limit for learning cards
        self.reps = 0            # The number of today already reviewed cards
        self.today = None        # The number of days since the collection creation
        self._lrnCutoff = 0      # The timestamp in seconds to determine the learn ahead limit
        self.reset()

    def getCard(self):
        "Pop the next card from the queue. None if finished."
        self._checkDay()
        card = self._getCard()
        if card:
            self.reps += 1
            return card

    def reset(self):
        self._updateCutoff()
        self._resetLrn()
        self._resetRev()
        self._resetNew()

    def answerCard(self, card, ease):
        assert 1 <= ease <= 4
        assert 0 <= card.queue <= 4

        card.reps += 1

        if card.queue == 0:
            # came from the new queue, move to learning
            card.queue = 1
            card.type = 1
            # init reps to graduation
            card.left = self._startingLeft(card)

        if card.queue in [1, 3]:
            self._answerLrnCard(card, ease)
        elif card.queue == 2:
            self._answerRevCard(card, ease)
        else:
            assert 0

    # Getting the next card
    ##########################################################################

    def _getCard(self):
        "Return the next due card id, or None."
        # learning card due?
        c = self._getLrnCard()
        if c:
            return c

        # new first, or time for one?
        if self._timeForNewCard():
            c = self._getNewCard()
            if c:
                return c

        # card due for review?
        c = self._getRevCard()
        if c:
            return c

        # day learning card due?
        c = self._getLrnDayCard()
        if c:
            return c

        # new cards left?
        c = self._getNewCard()
        if c:
            return c

        # collapse or finish
        return self._getLrnCard(collapse=True)

    # New cards
    ##########################################################################

    def _resetNew(self):
        self._newQueue = []
        self._updateNewCardRatio()
    # Reinitializes the new queue

    def _fillNew(self):
        if self._newQueue:
            return True
        lim = min(self.queueLimit, self.col.deckConf["new"]["perDay"])
        self._newQueue = list(filter(lambda card: card.queue == 0, self.col.cards))
        self._newQueue.sort(key=lambda card: card.due)
        self._newQueue = self._newQueue[:lim]
        if self._newQueue:
            return True

    def _getNewCard(self):
        if self._fillNew():
            return self._newQueue.pop()

    def _updateNewCardRatio(self):
        if self.col.colConf['newSpread'] == NEW_CARDS_DISTRIBUTE:
            if self._newQueue:
                newCount = len(self._newQueue)
                revCount = len(self._revQueue)
                self.newCardModulus = (
                    (newCount + revCount) // newCount)
                # if there are cards to review, ensure modulo >= 2
                if revCount:
                    self.newCardModulus = max(2, self.newCardModulus)
                return
        self.newCardModulus = 0 # = Do not distribute new cards

    def _timeForNewCard(self):
        "True if it's time to display a new card when distributing."
        if not self._newQueue:
            return False
        if self.col.colConf['newSpread'] == NEW_CARDS_LAST:
            return False
        elif self.col.colConf['newSpread'] == NEW_CARDS_FIRST:
            return True
        elif self.newCardModulus:
            return self.reps and self.reps % self.newCardModulus == 0

    # Learning queues
    ##########################################################################

    def _updateLrnCutoff(self, force):
        nextCutoff = intTime() + self.col.colConf['collapseTime']
        if nextCutoff - self._lrnCutoff > 60 or force:
            self._lrnCutoff = nextCutoff
            return True
        return False

    def _maybeResetLrn(self, force):
        if self._updateLrnCutoff(force):
            self._resetLrn()

    def _resetLrn(self):
        self._updateLrnCutoff(force=True)
        self._lrnQueue = []
        self._lrnDayQueue = []

    def _fillLrn(self):
        if self._lrnQueue:
            return True
        cutoff = intTime() + self.col.colConf['collapseTime']
        self._lrnQueue = list(filter(lambda card: card.queue == 1 and card.due < cutoff, self.col.cards))
        self._lrnQueue.sort(key=lambda card: card.id)
        self._lrnQueue = self._lrnQueue[:self.reportLimit]
        return self._lrnQueue

    def _getLrnCard(self, collapse=False):
        self._maybeResetLrn(force=collapse and not self._lrnDayQueue == 0)
        if self._fillLrn():
            return self._lrnQueue.pop()

    def _fillLrnDay(self):
        if self._lrnDayQueue:
            return True

        self._lrnDayQueue = list(filter(lambda card: card.queue == 3 and card.due <= self.today, self.col.cards))
        self._lrnDayQueue = self._lrnDayQueue[:self.queueLimit]
        if self._lrnDayQueue:
            # order
            r = random.Random()
            r.seed(self.today)
            r.shuffle(self._lrnDayQueue)
            return True

    def _getLrnDayCard(self):
        if self._fillLrnDay():
            return self._lrnDayQueue.pop()

    def _answerLrnCard(self, card, ease):
        conf = self._lrnConf(card)

        # immediate graduate?
        if ease == 4:
            self._rescheduleAsRev(card, conf, True)
        # next step?
        elif ease == 3:
            # graduation time?
            if (card.left%1000)-1 <= 0:
                self._rescheduleAsRev(card, conf, False)
            else:
                self._moveToNextStep(card, conf)
        elif ease == 2:
            self._repeatStep(card, conf)
        else:
            # back to first step
            self._moveToFirstStep(card, conf)

    def _updateRevIvlOnFail(self, card, conf):
        card.ivl = self._lapseIvl(card, conf)

    def _moveToFirstStep(self, card, conf):
        card.left = self._startingLeft(card)

        # relearning card?
        if card.type == 3:
            self._updateRevIvlOnFail(card, conf)

        return self._rescheduleLrnCard(card, conf)

    def _moveToNextStep(self, card, conf):
        # decrement real left count and recalculate left today
        left = (card.left % 1000) - 1
        card.left = self._leftToday(conf['delays'], left)*1000 + left

        self._rescheduleLrnCard(card, conf)

    def _repeatStep(self, card, conf):
        delay = self._delayForRepeatingGrade(conf, card.left)
        self._rescheduleLrnCard(card, conf, delay=delay)

    def _rescheduleLrnCard(self, card, conf, delay=None):
        # normal delay for the current step?
        if delay is None:
            delay = self._delayForGrade(conf, card.left)

        card.due = int(time.time() + delay)
        # due today?
        if card.due < self.dayCutoff:
            # add some randomness, up to 5 minutes or 25%
            maxExtra = min(300, int(delay*0.25))
            fuzz = random.randrange(0, maxExtra)
            card.due = min(self.dayCutoff-1, card.due + fuzz)
            card.queue = 1
        else:
            # the card is due in one or more days, so we need to use the
            # day learn queue
            ahead = ((card.due - self.dayCutoff) // 86400) + 1
            card.due = self.today + ahead
            card.queue = 3
        return delay

    def _delayForGrade(self, conf, left):
        left = left % 1000
        delay = conf['delays'][-left]
        return delay*60

    def _delayForRepeatingGrade(self, conf, left):
        # halfway between last and next
        delay1 = self._delayForGrade(conf, left)
        delay2 = self._delayForGrade(conf, left-1)
        avg = (delay1+max(delay1, delay2))//2
        return avg

    def _lrnConf(self, card):
        if card.type in (2, 3):
            return self.col.deckConf["lapse"]
        else:
            return self.col.deckConf["new"]

    def _rescheduleAsRev(self, card, conf, early):
        lapse = card.type in (2,3)

        if lapse:
            self._rescheduleGraduatingLapse(card)
        else:
            self._rescheduleNew(card, conf, early)

    def _rescheduleGraduatingLapse(self, card):
        card.due = self.today+card.ivl
        card.queue = 2
        card.type = 2

    def _startingLeft(self, card):
        conf = self._lrnConf(card)
        tot = len(conf['delays'])
        tod = self._leftToday(conf['delays'], tot)
        return tot + tod*1000

    def _leftToday(self, delays, left, now=None):
        "The number of steps that can be completed by the day cutoff."
        if not now:
            now = intTime()
        delays = delays[-left:]
        ok = 0
        for i in range(len(delays)):
            now += delays[i]*60
            if now > self.dayCutoff:
                break
            ok = i
        return ok+1

    def _graduatingIvl(self, card, conf, early, fuzz=True):
        if card.type in (2,3):
            return card.ivl
        if not early:
            # graduate
            ideal =  conf['ints'][0]
        else:
            # early remove
            ideal = conf['ints'][1]
        if fuzz:
            ideal = self._fuzzedIvl(ideal)
        return ideal

    def _rescheduleNew(self, card, conf, early):
        "Reschedule a new card that's graduated for the first time."
        card.ivl = self._graduatingIvl(card, conf, early)
        card.due = self.today+card.ivl
        card.factor = conf['initialFactor']
        card.type = card.queue = 2

    # Reviews
    ##########################################################################

    def _resetRev(self):
        self._revQueue = []
    # Reinitializes the review queue.

    def _fillRev(self):
        if self._revQueue:
            return True
        lim = min(self.queueLimit, self.col.deckConf["rev"]["perDay"])
        self._revQueue = list(filter(lambda card: card.queue == 2 and card.due <= self.today, self.col.cards))
        self._revQueue.sort(key=lambda card: card.due)
        self._revQueue = self._revQueue[:lim]

        if self._revQueue:
            r = random.Random()
            r.seed(self.today)
            r.shuffle(self._revQueue)
            return True

    def _getRevCard(self):
        if self._fillRev():
            return self._revQueue.pop()

    # Answering a review card
    ##########################################################################

    def _answerRevCard(self, card, ease):
        if ease == 1:
            self._rescheduleLapse(card)
        else:
            self._rescheduleRev(card, ease)

    def _rescheduleLapse(self, card):
        conf = self.col.deckConf["lapse"]

        card.lapses += 1
        card.factor = max(1300, card.factor-200)

        suspended = self._checkLeech(card, conf)

        if not suspended:
            card.type = 3
            delay = self._moveToFirstStep(card, conf)
        else:
            # no relearning steps
            self._updateRevIvlOnFail(card, conf)
            delay = 0

        return delay

    def _lapseIvl(self, card, conf):
        ivl = max(1, conf['minInt'], int(card.ivl*conf['mult']))
        return ivl

    def _rescheduleRev(self, card, ease):
        # update interval
        self._updateRevIvl(card, ease)

        # then the rest
        card.factor = max(1300, card.factor+[-150, 0, 150][ease-2])
        card.due = self.today + card.ivl

    def nextIvl(self, card, ease):
        "Return the next interval for CARD, in seconds."
        # (re)learning?
        if card.queue in [0, 1, 3]:
            return self._nextLrnIvl(card, ease)
        elif ease == 1:
            # lapse
            conf = self._lapseConf(card)
            if conf['delays']:
                return conf['delays'][0]*60
            return self._lapseIvl(card, conf)*86400
        else:
            # review
            return self._nextRevIvl(card, ease, fuzz=False)*86400

    def _nextLrnIvl(self, card, ease):
        if card.queue == 0:
            card.left = self._startingLeft(card)
        conf = self._lrnConf(card)
        if ease == 1:
            # fail
            return self._delayForGrade(conf, len(conf['delays']))
        elif ease == 2:
            return self._delayForRepeatingGrade(conf, card.left)
        elif ease == 4:
            return self._graduatingIvl(card, conf, True, fuzz=False) * 86400
        else: # ease == 3
            left = card.left%1000 - 1
            if left <= 0:
                # graduate
                return self._graduatingIvl(card, conf, False, fuzz=False) * 86400
            else:
                return self._delayForGrade(conf, left)

    # Interval management
    ##########################################################################

    def _nextRevIvl(self, card, ease, fuzz):
        "Next review interval for CARD, given EASE."
        delay = self._daysLate(card)
        conf = self.col.deckConf["rev"]
        fct = card.factor / 1000
        hardFactor = conf.get("hardFactor", 1.2)
        if hardFactor > 1:
            hardMin = card.ivl
        else:
            hardMin = 0
        ivl2 = self._constrainedIvl(card.ivl * hardFactor, conf, hardMin, fuzz)
        if ease == 2:
            return ivl2

        ivl3 = self._constrainedIvl((card.ivl + delay // 2) * fct, conf, ivl2, fuzz)
        if ease == 3:
            return ivl3

        ivl4 = self._constrainedIvl(
            (card.ivl + delay) * fct * conf['ease4'], conf, ivl3, fuzz)
        return ivl4

    def _fuzzedIvl(self, ivl):
        min, max = self._fuzzIvlRange(ivl)
        return random.randint(min, max)

    def _fuzzIvlRange(self, ivl):
        if ivl < 2:
            return [1, 1]
        elif ivl == 2:
            return [2, 3]
        elif ivl < 7:
            fuzz = int(ivl*0.25)
        elif ivl < 30:
            fuzz = max(2, int(ivl*0.15))
        else:
            fuzz = max(4, int(ivl*0.05))
        # fuzz at least a day
        fuzz = max(fuzz, 1)
        return [ivl-fuzz, ivl+fuzz]

    def _constrainedIvl(self, ivl, conf, prev, fuzz):
        ivl = int(ivl * conf.get('ivlFct', 1))
        if fuzz:
            ivl = self._fuzzedIvl(ivl)
        ivl = max(ivl, prev+1, 1)
        ivl = min(ivl, conf['maxIvl'])
        return int(ivl)

    def _daysLate(self, card):
        "Number of days later than scheduled."
        return max(0, self.today - card.due)

    def _updateRevIvl(self, card, ease):
        card.ivl = self._nextRevIvl(card, ease, fuzz=True)

    # Leeches
    ##########################################################################

    def _checkLeech(self, card, conf):
        "Leech handler. True if card was a leech."
        lf = conf['leechFails']
        if not lf:
            return
        # if over threshold or every half threshold reps after that
        if card.lapses >= lf:
            # add a leech tag
            f = card.note
            f.addTag("leech")
            # Suspend
            card.queue = -1
            return True

    # Daily cutoff
    ##########################################################################

    def _updateCutoff(self):
        # days since col created
        self.today = self._daysSinceCreation()
        # end of day cutoff
        self.dayCutoff = self._dayCutoff()

    def _checkDay(self):
        # check if the day has rolled over
        if time.time() > self.dayCutoff:
            self.reset()

    def _dayCutoff(self):
        date = datetime.datetime.today()
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        if date < datetime.datetime.today():
            date = date + datetime.timedelta(days=1)
        stamp = int(time.mktime(date.timetuple()))
        return stamp

    def _daysSinceCreation(self):
        startDate = datetime.datetime.fromtimestamp(self.col.crt)
        return int((time.time() - time.mktime(startDate.timetuple())) // 86400)

    # Debug
    ##########################################################################

    def dump(self):
        print("+---------------+------------+------+-------+-------+--------+------+--------+------+------------+")
        print("| id            | crt        | type | queue | ivl   | factor | reps | lapses | left | due        |")
        print("+---------------+------------+------+-------+-------+--------+------+--------+------+------------+")
        for c in self.col.cards:
            print(f"| {c.id:>12} | {c.crt} | {c.type:>4} | {c.queue:>5} | {c.ivl:>5} | {c.factor:>6} | {c.reps:>4} | {c.lapses:>6} | {c.left:>4} | {c.due:>10} |")
            print("+---------------+------------+------+-------+-------+--------+------+--------+------+------------+")

        print("")

        def dump_queue(name, q):
            print("\t        " + ("+----" * len(q)) + "+")
            print(f"\t{name:<7} " + "".join([f"| {c.id:>12} " for c in q]) + "|")
            print("\t        " + ("+----" * len(q)) + "+")

        print("Queues:")
        dump_queue("New", self._newQueue)
        dump_queue("Lrn", self._lrnQueue)
        dump_queue("LrnDay", self._lrnDayQueue)
        dump_queue("Rev", self._revQueue)
