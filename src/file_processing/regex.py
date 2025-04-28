import re, unicodedata, heapq
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from functools import lru_cache
from collections import defaultdict

RAW_CONFUSIONS: Dict[str, List[Tuple[str, int]]] = {
    "0": [("O", 1), ("D", 2), ("Q", 3)],
    "1": [("I", 1), ("L", 1), ("7", 2), ("T", 3)],
    "2": [("Z", 1)],
    "3": [("E", 2)],
    "4": [("A", 2)],
    "5": [("S", 1)],
    "6": [("G", 2), ("9", 3)],
    "7": [("1", 2), ("T", 2)],
    "8": [("B", 1)],
    "9": [("G", 2), ("Q", 2)],
    "O": [("0", 1), ("D", 2), ("Q", 2)],
    "D": [("0", 2), ("O", 2)],
    "Q": [("0", 2), ("O", 2), ("9", 2)],
    "I": [("1", 1), ("L", 1)],
    "L": [("1", 1), ("I", 1)],
    "Z": [("2", 1)],
    "S": [("5", 1)],
    "B": [("8", 1)],
    "E": [("3", 2), ("F", 3)],
    "G": [("6", 2), ("9", 2)],
    "T": [("7", 2), ("1", 3)],
    "C": [("G", 3), ("O", 3)],
    "F": [("E", 3)],
    "M": [("N", 3)],
    "N": [("M", 3)],
}
CONFUSIONS: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
for k, lst in RAW_CONFUSIONS.items():
    k = k.upper()
    CONFUSIONS[k].extend(lst)
    for alt, c in lst:
        CONFUSIONS[alt.upper()].append((k, c))
for k, lst in CONFUSIONS.items():
    best: Dict[str, int] = {}
    for ch, c in lst:
        best[ch] = min(best.get(ch, 9), c)
    CONFUSIONS[k] = sorted(best.items(), key=lambda t: (t[1], t[0]))

ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_DASHES = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212"}
FW_START, FW_END = 0xFF01, 0xFF5E
_COMBINING = {c for c in range(0x300, 0x370)}
_TOKEN_RE = re.compile(r"(\\d|\[0-9\])|([A-Za-z])|\[([A-Z0-9]+)\]|.", re.X)

# ---------------------------------------------------------------------------

def _halfwidth(ch: str) -> str:
    o = ord(ch)
    return chr(o - 0xFEE0) if FW_START <= o <= FW_END else ch

@lru_cache(maxsize=2048)
def normalise(text: str, strip_diacritics: bool = True) -> str:
    text = unicodedata.normalize("NFC", text or "")
    text = " ".join(text.split())
    text = "".join("-" if ch in _DASHES else ch for ch in text)
    text = "".join(_halfwidth(ch) for ch in text)
    if strip_diacritics:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if ord(ch) not in _COMBINING)
    return text.upper()

# ---------------------------------------------------------------------------

@lru_cache(maxsize=256)
def _allowed_chars(pattern: str) -> List[Set[str]]:
    """Return the set of *legal* characters for each position in the pattern."""
    res: List[Set[str]] = []
    i = 0
    while i < len(pattern):
        m = _TOKEN_RE.match(pattern, i)
        if not m:          # any literal we didn't understand
            res.append(set(ALNUM + "-"))
            i += 1
            continue
        tok = m.group(0)
        i = m.end()
        if tok in (r"\d", "[0-9]"):
            res.append(set("0123456789"))
        elif len(tok) == 1 and tok.isalpha():
            res.append({tok.upper()})
        elif m.group(3):
            res.append(set(m.group(3).upper()))
        else:
            res.append(set(ALNUM + "-"))
    return res

# ---------------------------------------------------------------------------

def _heuristic(s: str, allowed: List[Set[str]]) -> int:
    """Minimum edits *still required* to make s legal (admissible for A*)."""
    return sum(ch not in allowed[i] for i, ch in enumerate(s[:len(allowed)]))

def correct_to_pattern(
    pattern: str | re.Pattern,
    raw: str,
    *,
    strip_diacritics: bool = True,
    allow_transpose: bool = True,
    allow_insertion: bool = True,
    max_edits: int = 1000,
) -> Optional[str]:
    # ---------- local helpers (use enclosing scope variables) --------------
    def _push(candidate: str, g: int, c: int):
        h = _heuristic(candidate, allowed)
        heapq.heappush(pq, (g + h, g, c, candidate))

    def _record_better(s: str, edits: int, cost: int, seen: Dict[str, Tuple[int, int]]) -> bool:
        best = seen.get(s)
        if best is None or edits < best[0] or (edits == best[0] and cost < best[1]):
            seen[s] = (edits, cost)
            return True
        return False

    rx = re.compile(pattern) if isinstance(pattern, str) else pattern
    wants_hyphen = "-" in rx.pattern
    allowed = _allowed_chars(rx.pattern)
    max_len = len(allowed) + max_edits        # simple length guard

    start = normalise(raw, strip_diacritics=strip_diacritics)
    if rx.fullmatch(start):
        return start

    # ---------- A* SEARCH ---------------------------------------------------
    # heap item: (f = g + h, g = edits, cost, candidate_string)
    h0 = _heuristic(start, allowed)
    pq: List[Tuple[int, int, int, str]] = [(h0, 0, 0, start)]
    seen: Dict[str, Tuple[int, int]] = {start: (0, 0)}

    while pq:
        f, edits, cost, s = heapq.heappop(pq)
        if edits > max_edits:
            continue

        # Generate neighbours ------------------------------------------------
        L = len(s)
        # 1. single-char substitutions from CONFUSIONS
        for i, ch in enumerate(s):
            for alt, pen in CONFUSIONS.get(ch, ()):
                if alt in allowed[i] and alt != ch:
                    cand = s[:i] + alt + s[i + 1 :]
                    g = edits + 1
                    new_cost = cost + pen
                    if _record_better(cand, g, new_cost, seen):
                        if rx.fullmatch(cand):
                            return cand
                        _push(candidate=cand, g=g, c=new_cost)

        # 2. deletion
        for i in range(L):
            cand = s[:i] + s[i + 1 :]
            if len(cand) and len(cand) <= max_len and _record_better(cand, edits + 1, cost + 1, seen):
                if rx.fullmatch(cand):
                    return cand
                _push(candidate=cand, g=edits + 1, c=cost + 1)

        # 3. hyphen insertion where pattern wants it
        if wants_hyphen and "-" not in s:
            for i in range(1, L):
                cand = s[:i] + "-" + s[i:]
                if len(cand) <= max_len and _record_better(cand, edits + 1, cost + 1, seen):
                    if rx.fullmatch(cand):
                        return cand
                    _push(candidate=cand, g=edits + 1, c=cost + 1)

        # 4. transposition
        if allow_transpose:
            for i in range(L - 1):
                if s[i] == s[i + 1]:
                    continue
                cand = s[:i] + s[i + 1] + s[i] + s[i + 2 :]
                if _record_better(cand, edits + 1, cost + 1, seen):
                    if rx.fullmatch(cand):
                        return cand
                    _push(candidate=cand, g=edits + 1, c=cost + 1)

        # 5. insertion of any legal char
        if allow_insertion:
            for i in range(L + 1):
                legal_here = allowed[i] if i < len(allowed) else allowed[-1]
                for ins in legal_here:
                    cand = s[:i] + ins + s[i:]
                    if len(cand) <= max_len and _record_better(cand, edits + 1, cost + 2, seen):
                        if rx.fullmatch(cand):
                            return cand
                        _push(candidate=cand, g=edits + 1, c=cost + 2)

    return None  # exhausted search

if __name__ == "__main__":
    pattern = r"USER\d{3}[A-Z]"
    samples = [
        " user–123a ",
        "USEER-123A",
        "user123a",
        "USR-123A",
        "us3r-12ba",
    ]
    for txt in samples:
        fix = correct_to_pattern(pattern, txt)
        print(f"{txt!r:<15} → {fix}")
