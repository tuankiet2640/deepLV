"""Shared machinery for the OOXML formats.

DOCX and PPTX store text the same way: a paragraph element holds a sequence of
runs, each run carries its own formatting and wraps a text node, and structural
markers such as line breaks sit between runs. Only the tag names differ, so the
traversal and the write-back are described once here and configured per format.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from src.api.services.document_format.redistribute import distribute, group_slots

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def a(tag: str) -> str:
    return f"{{{A_NS}}}{tag}"


@dataclass(frozen=True)
class RowSpec:
    """Tag names and filters describing one OOXML dialect."""

    paragraph: str
    run: str
    text: str
    run_props: str
    # Elements that separate text into independent units. Keeping text grouped
    # between them means tabs and manual line breaks never move.
    breaks: frozenset[str] = frozenset()
    # Subtrees whose text must not be translated: field codes, deleted
    # revisions, auto-generated slide numbers.
    skip: frozenset[str] = frozenset()
    # Run properties that differ without changing appearance, so runs split only
    # by proofing or revision metadata can be merged into one slot.
    ignored_props: frozenset[str] = frozenset()
    ignored_prop_attrs: frozenset[str] = field(default_factory=frozenset)


def format_key(properties: Any, spec: RowSpec) -> str:
    """A comparable fingerprint of a run's visual formatting."""
    if properties is None:
        return ""
    clone = etree.fromstring(etree.tostring(properties))
    for child in list(clone):
        if child.tag in spec.ignored_props:
            clone.remove(child)
    for name in list(clone.attrib):
        if name in spec.ignored_prop_attrs:
            del clone.attrib[name]
    return etree.tostring(clone, method="c14n").decode("utf-8")


def set_preserving_space(node: Any, text: str) -> None:
    """Write text into an OOXML text node, keeping edge whitespace significant."""
    node.text = text
    if text != text.strip():
        node.set(XML_SPACE, "preserve")
    elif node.get(XML_SPACE) is not None:
        del node.attrib[XML_SPACE]


def paragraph_rows(paragraph: Any, spec: RowSpec) -> list[list[Any]]:
    """Group a paragraph's own text nodes into rows, split at structural breaks.

    Nested paragraphs — a Word text box anchored inside a run — are skipped so
    their text is not claimed twice; the caller's paragraph loop reaches them
    separately.
    """
    rows: list[list[Any]] = [[]]

    def visit(element: Any) -> None:
        for child in element:
            tag = child.tag
            if tag == spec.paragraph or tag in spec.skip:
                continue
            if tag == spec.text:
                rows[-1].append(child)
            elif tag in spec.breaks:
                if rows[-1]:
                    rows.append([])
            elif len(child):
                visit(child)

    visit(paragraph)
    return [row for row in rows if row]


class OoxmlTextRow:
    """A stretch of text nodes inside one paragraph, uninterrupted by breaks."""

    def __init__(self, nodes: list[Any], context: str, spec: RowSpec) -> None:
        self._nodes = nodes
        self._context = context
        self._spec = spec

    @property
    def context(self) -> str:
        return self._context

    def get_text(self) -> str:
        return "".join(node.text or "" for node in self._nodes)

    def set_text(self, value: str) -> None:
        groups = group_slots([self._slot_key(node) for node in self._nodes])
        weights = [sum(len(self._nodes[i].text or "") for i in group) for group in groups]

        for group, piece in zip(groups, distribute(value, weights), strict=True):
            set_preserving_space(self._nodes[group[0]], piece)
            # A merged slot writes everything to its first node, so the rest are
            # emptied rather than left holding stale source text.
            for index in group[1:]:
                set_preserving_space(self._nodes[index], "")
        self.after_set(value)

    def after_set(self, value: str) -> None:
        """Hook for format-specific bookkeeping once text is written."""

    def _run_of(self, node: Any) -> Any:
        run = node.getparent()
        return run if run is not None and run.tag == self._spec.run else None

    def _slot_key(self, node: Any) -> str:
        run = self._run_of(node)
        properties = run.find(self._spec.run_props) if run is not None else None
        return format_key(properties, self._spec)

    def runs(self) -> Iterator[Any]:
        for node in self._nodes:
            run = self._run_of(node)
            if run is not None:
                yield run
