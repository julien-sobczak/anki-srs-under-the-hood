# Anki SRS Under the Hood

## Organization

```shell
$ tree .
.
├── README.md
└── anki
|   └── schedv2.py            # Ex: https://faqs.ankiweb.net/what-spaced-repetition-algorithm.html
|   └── test_schedv2.py       # Test suite for schedv2.py
|   └── schedv2_minimal.py    # Same but with minimal features
|   └── schedv2_annotated.py  # Same but with annotations
└── leitner
|   └── original.py # Ex: https://en.wikipedia.org/wiki/Leitner_system
|   └── modern.py   # Ex: https://leverageedu.com/blog/leitner-system/
└── supermemo
    └── sm0.py      # Ex: http://super-memory.com/articles/paper.htm
    └── sm2.py      # Ex: http://super-memory.com/english/ol/sm2.htm
```
