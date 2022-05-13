import os

"""
How to reproduce the test?

1. Run
     open /Applications/Anki.app --args -b $PWD/AnkiTest
2. Rename the deck `Default` in `General`
3. Add a few notes inside this deck:
     Front: "Question 1", Back: "Answer 1", Tags: [demo]
     Front: "Question 2", Back: "Answer 2", Tags: [demo]
     Front: "Question 3", Back: "Answer 3", Tags: [special]
4. Create a filtered deck using the query `tag:special`
5. Exit Anki

Then, run this script to dump various information about the Anki collection:

    $ pip3 install aqt==2.1.49
    $ pip3 install anki==2.1.49
    $ python3 dump.py

You can also check the Anki database directly using a GUI:

    $ brew install --cask db-browser-for-sqlite
    # Then select the file $PWD/AnkiTest/collection.anki2
"""

from anki.storage import Collection

# https://stackoverflow.com/a/59128615
from pprint import pprint
from inspect import getmembers
from types import FunctionType

def attributes(obj):
    disallowed_names = {
      name for name, value in getmembers(type(obj))
        if isinstance(value, FunctionType)}
    return {
      name: getattr(obj, name) for name in dir(obj)
        if name[0] != '_' and name not in disallowed_names and hasattr(obj, name)}

def print_attributes(obj):
    pprint(attributes(obj))



# Open Anki
anki_home = '/Users/julien/Workshop/anki-srs-under-the-hood/anki/AnkiTest/User 1'
anki_collection_path = os.path.join(anki_home, "collection.anki2")
col = Collection(anki_collection_path, log=True)

# 2 collections = General (3 cards with 2 notes each) + Temp (filtered deck on `tag:special`)
deck_default = col.decks.by_name('General')
deck_dyn = col.decks.by_name('Temp')

#
# Col
#

basicModel = col.models.by_name("Basic")
basicReverseModel = col.models.by_name("Basic (optional reversed card)")
pprint(col.models.field_map(basicModel))
# {'Back': (1,
#           {'font': 'Arial',
#            'name': 'Back',
#            'ord': 1,
#            'rtl': False,
#            'size': 20,
#            'sticky': False}),
#  'Front': (0,
#            {'font': 'Arial',
#             'name': 'Front',
#             'ord': 0,
#             'rtl': False,
#             'size': 20,
#             'sticky': False})}
pprint(col.models.field_map(basicReverseModel))
# {'Add Reverse': (2,
#                  {'font': 'Arial',
#                   'name': 'Add Reverse',
#                   'ord': 2,
#                   'rtl': False,
#                   'size': 20,
#                   'sticky': False}),
#  'Back': (1,
#           {'font': 'Arial',
#            'name': 'Back',
#            'ord': 1,
#            'rtl': False,
#            'size': 20,
#            'sticky': False}),
#  'Front': (0,
#            {'font': 'Arial',
#             'name': 'Front',
#             'ord': 0,
#             'rtl': False,
#             'size': 20,
#             'sticky': False})}

print(basicModel['type']) # 0 == MODEL_STD
ok = []
for t in basicModel['tmpls']:
    ok.append(t)
pprint(ok)
# [{'afmt': '{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}',
#   'bafmt': '',
#   'bfont': '',
#   'bqfmt': '',
#   'bsize': 0,
#   'did': None,
#   'name': 'Card 1',
#   'ord': 0,
#   'qfmt': '{{Front}}'}]


#
# Deck
#
print(col.decks.all_config()) # Returns only the Default
# [
#     {
#         "id": 1,
#         "mod": 0,
#         "name": "Default",
#         "usn": 0,
#         "maxTaken": 60,
#         "autoplay": true,
#         "timer": 0,
#         "replayq": true,
#         "new": {
#             "bury": false,
#             "delays": [
#                 1.0,
#                 10.0
#             ],
#             "initialFactor": 2500,
#             "ints": [
#                 1,
#                 4,
#                 0
#             ],
#             "order": 1,
#             "perDay": 20
#         },
#         "rev": {
#             "bury": false,
#             "ease4": 1.3,
#             "ivlFct": 1.0,
#             "maxIvl": 36500,
#             "perDay": 200,
#             "hardFactor": 1.2
#         },
#         "lapse": {
#             "delays": [
#                 10.0
#             ],
#             "leechAction": 1,
#             "leechFails": 8,
#             "minInt": 1,
#             "mult": 0.0
#         },
#         "dyn": false,
#         "newMix": 0,
#         "newPerDayMinimum": 0,
#         "interdayLearningMix": 0,
#         "reviewOrder": 0,
#         "newSortOrder": 0,
#         "newGatherPriority": 0
#     }
# ]

print("==========================")
print(dir(deck_default))
# ['__class__', '__class_getitem__', '__contains__', '__delattr__', '__delitem__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__ior__', '__iter__', '__le__', '__len__', '__lt__', '__ne__', '__new__', '__or__', '__reduce__', '__reduce_ex__', '__repr__', '__reversed__', '__ror__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__', 'clear', 'copy', 'fromkeys', 'get', 'items', 'keys', 'pop', 'popitem', 'setdefault', 'update', 'values']
print(type(deck_default))
# <class 'dict'>
print(col.decks.config_dict_for_deck_id(deck_default['id']))
# {
#     "id": 1,
#     "mod": 0,
#     "name": "Default",
#     "usn": 0,
#     "maxTaken": 60,
#     "autoplay": True,
#     "timer": 0,
#     "replayq": True,
#     "new": {
#         "bury": False,
#         "delays": [
#             1.0,
#             10.0
#         ],
#         "initialFactor": 2500,
#         "ints": [
#             1,
#             4,
#             0
#         ],
#         "order": 1,
#         "perDay": 20
#     },
#     "rev": {
#         "bury": False,
#         "ease4": 1.3,
#         "ivlFct": 1.0,
#         "maxIvl": 36500,
#         "perDay": 200,
#         "hardFactor": 1.2
#     },
#     "lapse": {
#         "delays": [
#             10.0
#         ],
#         "leechAction": 1,
#         "leechFails": 8,
#         "minInt": 1,
#         "mult": 0.0
#     },
#     "dyn": False,
#     "newMix": 0,
#     "newPerDayMinimum": 0,
#     "interdayLearningMix": 0,
#     "reviewOrder": 0,
#     "newSortOrder": 0,
#     "newGatherPriority": 0
# }

print("==========================")
print(dir(deck_dyn))
# ['__class__', '__class_getitem__', '__contains__', '__delattr__', '__delitem__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__ior__', '__iter__', '__le__', '__len__', '__lt__', '__ne__', '__new__', '__or__', '__reduce__', '__reduce_ex__', '__repr__', '__reversed__', '__ror__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__', 'clear', 'copy', 'fromkeys', 'get', 'items', 'keys', 'pop', 'popitem', 'setdefault', 'update', 'values']
print(col.decks.config_dict_for_deck_id(deck_dyn['id']))
# {
#     "id": 1652712502103,
#     "mod": 1652712591,
#     "name": "Temp",
#     "usn": -1,
#     "lrnToday": [
#         0,
#         0
#     ],
#     "revToday": [
#         0,
#         0
#     ],
#     "newToday": [
#         0,
#         0
#     ],
#     "timeToday": [
#         0,
#         0
#     ],
#     "collapsed": True,
#     "browserCollapsed": True,
#     "desc": "",
#     "dyn": 1,
#     "resched": True,
#     "terms": [
#         [
#             "deck:Default tag:special",
#             100,
#             1
#         ]
#     ],
#     "separate": True,
#     "delays": None,
#     "previewDelay": 10
# }


cards = col.find_cards("")
print(len(cards))
# 3
print(dir(cards[0]))
# ['__abs__', '__add__', '__and__', '__bool__', '__ceil__', '__class__', '__delattr__', '__dir__', '__divmod__', '__doc__', '__eq__', '__float__', '__floor__', '__floordiv__', '__format__', '__ge__', '__getattribute__', '__getnewargs__', '__gt__', '__hash__', '__index__', '__init__', '__init_subclass__', '__int__', '__invert__', '__le__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', '__neg__', '__new__', '__or__', '__pos__', '__pow__', '__radd__', '__rand__', '__rdivmod__', '__reduce__', '__reduce_ex__', '__repr__', '__rfloordiv__', '__rlshift__', '__rmod__', '__rmul__', '__ror__', '__round__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__', '__rxor__', '__setattr__', '__sizeof__', '__str__', '__sub__', '__subclasshook__', '__truediv__', '__trunc__', '__xor__', 'as_integer_ratio', 'bit_length', 'conjugate', 'denominator', 'from_bytes', 'imag', 'numerator', 'real', 'to_bytes']
print_attributes(cards[0])
