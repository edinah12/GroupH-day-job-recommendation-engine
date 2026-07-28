"""
Typo-tolerant ("fuzzy") keyword search helpers.

Plain ``icontains`` matching only finds a keyword if it is spelled
correctly and appears as a literal substring. These helpers add a second,
forgiving pass on top of that: if a word in the search is slightly
misspelled or is a close variant of a word that actually appears (e.g.
"developr" -> "Developer", "enginer" -> "Engineer", "managr" -> "Manager"),
it still matches. This is built entirely on Python's built-in ``difflib``,
so it needs no extra dependencies and works the same wherever it's used -
job listings, the home page search, and company search all share this
single implementation.
"""
import difflib
import re

from django.db.models import Q

_WORD_RE = re.compile(r"[a-z0-9]+")

# Words shorter than this are compared literally rather than fuzzily,
# since fuzzy-matching very short strings produces too many false positives
# (e.g. "js" would loosely match dozens of unrelated 2-letter fragments).
MIN_FUZZY_LENGTH = 4

# How close a word has to be (0-1, higher = stricter) to count as a match.
# 0.82 reliably catches real-world typos (missing/swapped/doubled letters,
# e.g. "developr"->"developer" is 0.94, "compnay"->"company" is 0.86,
# "mikrosoft"->"microsoft" is 0.89) while staying strict enough to avoid
# matching genuinely different words that merely look similar (e.g.
# "devops"->"develop" is 0.77, well below this cutoff).
DEFAULT_CUTOFF = 0.82


def _tokenize(text):
    """Lowercase a string into a list of alphanumeric word tokens."""
    return _WORD_RE.findall((text or "").lower())


def _build_exact_query(fields, term):
    """OR-combine `field__icontains=term` lookups across the given fields."""
    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": term})
    return query


def _word_matches(query_word, haystack_words, cutoff):
    if len(query_word) < MIN_FUZZY_LENGTH:
        return query_word in haystack_words
    if query_word in haystack_words:
        return True
    return bool(difflib.get_close_matches(query_word, haystack_words, n=1, cutoff=cutoff))


def fuzzy_filter(queryset, term, exact_fields, text_fn, cutoff=DEFAULT_CUTOFF):
    """
    Filter `queryset` by a free-text `term`, tolerating typos and close
    misspellings, without requiring any database extensions.

    Combines two passes and returns their union:
      1. Exact pass (DB-level, fast) - a plain ``icontains`` match across
         `exact_fields` (e.g. ["title", "company__name"]).
      2. Fuzzy pass (Python-level) - each word in `term` is compared
         against every word in `text_fn(obj)` for every candidate row;
         a record matches if any word is an exact or close match.

    `text_fn` should return one combined searchable string per object
    (e.g. title + company name + description + skills).

    If `term` is blank, `queryset` is returned unchanged.
    """
    term = (term or "").strip()
    if not term:
        return queryset

    exact_ids = set(
        queryset.filter(_build_exact_query(exact_fields, term)).values_list("id", flat=True)
    )

    query_words = _tokenize(term)
    fuzzy_ids = set()
    if query_words:
        for obj in queryset:
            haystack_words = set(_tokenize(text_fn(obj)))
            if not haystack_words:
                continue
            if any(_word_matches(qw, haystack_words, cutoff) for qw in query_words):
                fuzzy_ids.add(obj.id)

    matched_ids = exact_ids | fuzzy_ids
    return queryset.filter(id__in=matched_ids)
