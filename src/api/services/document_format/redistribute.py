"""Spread a translated string back across the formatting slots it came from.

A word-processor paragraph is stored as a sequence of runs, each carrying its own
formatting. "The **quick** brown fox" is three runs. Translating run by run
destroys quality, because each run is a sentence fragment with no context, so the
whole paragraph is translated as one string and then split back up here.

The split is proportional to the original slot lengths and snapped to word
boundaries. It cannot be exact — target languages reorder words — but it keeps
bold/italic/coloured spans roughly over the text they belonged to, and it is
exact in the common case of a paragraph with a single formatting slot.
"""

# How far from the proportional cut we are willing to move to reach a space.
_SNAP_WINDOW = 12


def distribute(text: str, weights: list[int]) -> list[str]:
    """Split ``text`` into ``len(weights)`` pieces sized proportionally to weights.

    Concatenating the result always reproduces ``text`` exactly, so no characters
    are lost or duplicated regardless of how the cuts land.
    """
    if not weights:
        return []
    if len(weights) == 1:
        return [text]

    total = sum(weights)
    if total <= 0:
        # Nothing to go on; put everything in the first slot.
        return [text] + [""] * (len(weights) - 1)

    pieces: list[str] = []
    cursor = 0
    running = 0
    for weight in weights[:-1]:
        running += weight
        target = round(len(text) * running / total)
        cut = _snap_to_boundary(text, target, cursor)
        pieces.append(text[cursor:cut])
        cursor = cut
    pieces.append(text[cursor:])
    return pieces


def _snap_to_boundary(text: str, target: int, floor: int) -> int:
    """Move ``target`` to the nearest word boundary, staying within bounds.

    Languages that do not use spaces simply get the proportional cut, since no
    boundary is found inside the window.
    """
    target = max(floor, min(target, len(text)))
    if target in (floor, len(text)):
        return target

    best = None
    for offset in range(_SNAP_WINDOW + 1):
        for candidate in (target - offset, target + offset):
            if floor < candidate < len(text) and text[candidate - 1].isspace():
                best = candidate
                break
        if best is not None:
            break
    return best if best is not None else target


def group_slots(keys: list[str]) -> list[list[int]]:
    """Collapse consecutive identical formatting keys into one slot.

    Word and PowerPoint split runs on edit history, spell-check state and
    revision ids, so a visually uniform paragraph is routinely stored as a dozen
    identically formatted runs. Merging them first means the translation lands in
    one piece instead of being chopped at arbitrary positions.
    """
    groups: list[list[int]] = []
    previous: str | None = None
    for index, key in enumerate(keys):
        if previous is not None and key == previous:
            groups[-1].append(index)
        else:
            groups.append([index])
        previous = key
    return groups
