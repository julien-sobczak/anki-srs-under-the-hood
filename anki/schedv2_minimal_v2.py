"""
Same as schedv2_minimal_v1.py without the separation between
sub-day and day learning queues.
"""

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
    'collapseTime': 1200,
}

# Default deck configuration
deckDefaultConf = {
    'new': {
        'delays': [1, 10],
        'ints': [1, 4],
        'initialFactor': STARTING_FACTOR,
        'perDay': 20,
    },
    'lapse': {
        'delays': [10],
        'mult': 0,
        'minInt': 1,
        'leechFails': 8,
    },
    'rev': {
        'perDay': 200,
        'ease4': 1.3,
        'fuzz': 0.05,
        'ivlFct': 1,
        'maxIvl': 36500,
        'hardFactor': 1.2,
    },
}


class Collection:

    def __init__(self, id=None):
        d = datetime.datetime.today()
        d = datetime.datetime(d.year, d.month, d.day)
        self.crt = int(time.mktime(d.timetuple()))
        self.cards = []
        self.colConf = colDefaultConf
        self.deckConf = deckDefaultConf
        self.sched = Scheduler(self)

    def addNote(self, note):
        "Add a note to the collection. Return number of new cards."
        # add cards
        self.cards.append(self._newCard(note))

    def _newCard(self, note):
        "Create a new card."
        card = Card(note)
        return card

class Note:

    def __init__(self, id=None):
        if id:
            self.id = id
        else:
            self.id = intId()
        self.tags = []

    def addTag(self, tag):
        if not tag in self.tags:
            self.tags.append(tag)

class Card:

    def __init__(self, note, id=None):
        if id:
            self.id = id
        else:
            self.id = intId()
        self.note = note
        self.due = note.id
        self.crt = intTime()
        self.type = 0
        self.queue = 0
        self.ivl = 0
        self.factor = 0
        self.reps = 0
        self.lapses = 0
        self.left = 0
        self.due = self.id

class Scheduler:

    def __init__(self, col):
        self.col = col
        self.queueLimit = 50
        self.reportLimit = 1000
        self.reps = 0
        self.today = None
        self._lrnCutoff = 0
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

    def _fillLrn(self):
        if self._lrnQueue:
            return True
        cutoff = intTime() + self.col.colConf['collapseTime']
        self._lrnQueue = list(filter(lambda card: card.queue == 1 and card.due < cutoff, self.col.cards))
        self._lrnQueue.sort(key=lambda card: card.id)
        self._lrnQueue = self._lrnQueue[:self.reportLimit]
        return self._lrnQueue

    def _getLrnCard(self, collapse=False):
        self._maybeResetLrn(force=collapse)
        if self._fillLrn():
            return self._lrnQueue.pop()

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
        card.queue = 1
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

    # Testing
    ##########################################################################

    def nextIvl(self, card, ease):
        "Return the next interval for CARD, in seconds."
        # (re)learning?
        if card.queue in [0, 1]:
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
