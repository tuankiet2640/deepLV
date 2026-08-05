"""Glossary term substitution: provider-agnostic forced terminology.

MarianMT/HuggingFace/Google don't accept a system prompt (only OpenAI
does), so glossary enforcement can't be prompt injection. Instead: replace
matching source terms with a stable placeholder before calling the
provider, translate, then restore the placeholder to the user's target
term in the output. Works identically regardless of provider.

Best-effort, not guaranteed: if a provider's tokenizer mangles or drops a
placeholder, that term simply isn't restored -- the rest of the
translation still returns normally.
"""

import hashlib
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.glossary_term import GlossaryTerm

PLACEHOLDER_PREFIX = "⟦GT-"  # ⟦GT-
PLACEHOLDER_SUFFIX = "⟧"  # ⟧

MAX_TERMS_PER_USER = 500

# Word-boundary via \b is broken for terms that start/end on a
# non-alphanumeric character (e.g. "C++", "Acme Corp.", "AT&T") -- \b only
# fires at a \w/\W *transition*, and both sides are already non-word right
# at the edge of such a term, so it silently never matches. These
# lookarounds instead just require "not alphanumeric" on either side.
_NOT_ALNUM_BEFORE = r"(?<![A-Za-z0-9])"
_NOT_ALNUM_AFTER = r"(?![A-Za-z0-9])"


def _placeholder_for(source_term: str) -> str:
    digest = hashlib.sha256(source_term.strip().lower().encode()).hexdigest()[:20]
    return f"{PLACEHOLDER_PREFIX}{digest}{PLACEHOLDER_SUFFIX}"


def substitute(text: str, terms: list[GlossaryTerm]) -> str:
    """Replace glossary source terms with placeholders, longest term first
    so overlapping/nested terms (e.g. "Acme" and "Acme Corp") don't get
    partially clobbered."""
    for term in sorted(terms, key=lambda t: len(t.source_term), reverse=True):
        flags = 0 if term.case_sensitive else re.IGNORECASE
        pattern = _NOT_ALNUM_BEFORE + re.escape(term.source_term) + _NOT_ALNUM_AFTER
        text = re.sub(pattern, _placeholder_for(term.source_term), text, flags=flags)
    return text


def restore(text: str, terms: list[GlossaryTerm]) -> str:
    """Replace placeholders back with the user's target terms."""
    for term in terms:
        placeholder_pattern = re.escape(_placeholder_for(term.source_term))
        text = re.sub(placeholder_pattern, term.target_term, text, flags=re.IGNORECASE)
    return text


async def get_terms_for_pair(
    db: AsyncSession, user_id: uuid.UUID, source_lang: str, target_lang: str
) -> list[GlossaryTerm]:
    result = await db.execute(
        select(GlossaryTerm).where(
            GlossaryTerm.user_id == user_id,
            GlossaryTerm.source_lang == source_lang,
            GlossaryTerm.target_lang == target_lang,
        )
    )
    return list(result.scalars().all())
