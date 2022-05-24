# Anki SRS Under the Hood

## Organization

```shell
$ tree .
.
├── README.md
└── leitner
|   └── original.py # Ex: https://en.wikipedia.org/wiki/Leitner_system
|   └── modern.py   # Ex: https://leverageedu.com/blog/leitner-system/
└── supermemo
|   └── sm0.py      # Ex: http://super-memory.com/articles/paper.htm
|   └── sm2.py      # Ex: http://super-memory.com/english/ol/sm2.htm
└── anki
    └── schedv2.py            # Ex: https://faqs.ankiweb.net/what-spaced-repetition-algorithm.html
    └── test_schedv2.py       # Test suite for schedv2.py
    └── schedv2_minimal_v1.py # Same but with minimal features
    └── schedv2_minimal_v2.py # Same but with a single learning queue
    └── schedv2_minimal_v3.py # Same but without fuzzing
    └── schedv2_annotated.py  # Same but with annotations
```
