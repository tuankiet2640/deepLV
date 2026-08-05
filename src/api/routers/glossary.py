"""Glossary term management router.

Lets a user define forced source-term -> target-term overrides scoped to a
(source_lang, target_lang) pair. Applied automatically whenever that user
translates that pair (see src/api/services/glossary.py for the
substitution mechanism) -- no per-translation selection needed.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.glossary_term import GlossaryTerm
from src.api.models.user import User
from src.api.services.glossary import MAX_TERMS_PER_USER
from src.api.services.language_detect import SUPPORTED_LANGUAGES

log = structlog.get_logger()
router = APIRouter(prefix="/glossary", tags=["glossary"])


class GlossaryTermRequest(BaseModel):
    source_lang: str
    target_lang: str
    source_term: str
    target_term: str
    case_sensitive: bool = False


class UpdateGlossaryTermRequest(BaseModel):
    source_lang: str | None = None
    target_lang: str | None = None
    source_term: str | None = None
    target_term: str | None = None
    case_sensitive: bool | None = None


class GlossaryTermResponse(BaseModel):
    id: str
    source_lang: str
    target_lang: str
    source_term: str
    target_term: str
    case_sensitive: bool
    created_at: str


class GlossaryTermListResponse(BaseModel):
    terms: list[GlossaryTermResponse]


def _to_response(term: GlossaryTerm) -> GlossaryTermResponse:
    return GlossaryTermResponse(
        id=str(term.id),
        source_lang=term.source_lang,
        target_lang=term.target_lang,
        source_term=term.source_term,
        target_term=term.target_term,
        case_sensitive=term.case_sensitive,
        created_at=term.created_at.isoformat(),
    )


def _validate_lang(lang: str, field: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported {field}: {lang}",
        )


@router.post("", response_model=GlossaryTermResponse, status_code=status.HTTP_201_CREATED)
async def create_glossary_term(
    req: GlossaryTermRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GlossaryTermResponse:
    _validate_lang(req.source_lang, "source_lang")
    _validate_lang(req.target_lang, "target_lang")

    if not req.source_term.strip() or not req.target_term.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_term and target_term cannot be empty",
        )

    count_result = await db.execute(
        select(func.count()).select_from(GlossaryTerm).where(GlossaryTerm.user_id == user.id)
    )
    if count_result.scalar_one() >= MAX_TERMS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Glossary limit reached ({MAX_TERMS_PER_USER} terms per account)",
        )

    existing_result = await db.execute(
        select(GlossaryTerm).where(
            GlossaryTerm.user_id == user.id,
            GlossaryTerm.source_lang == req.source_lang,
            GlossaryTerm.target_lang == req.target_lang,
            func.lower(GlossaryTerm.source_term) == req.source_term.strip().lower(),
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A glossary term for this source term and language pair already exists",
        )

    term = GlossaryTerm(
        user_id=user.id,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        source_term=req.source_term.strip(),
        target_term=req.target_term.strip(),
        case_sensitive=req.case_sensitive,
    )
    db.add(term)
    await db.commit()
    await db.refresh(term)

    log.info("glossary_term_created", user_id=str(user.id), term_id=str(term.id))
    return _to_response(term)


@router.get("", response_model=GlossaryTermListResponse)
async def list_glossary_terms(
    source_lang: str | None = Query(default=None),
    target_lang: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GlossaryTermListResponse:
    query = select(GlossaryTerm).where(GlossaryTerm.user_id == user.id)
    if source_lang is not None:
        query = query.where(GlossaryTerm.source_lang == source_lang)
    if target_lang is not None:
        query = query.where(GlossaryTerm.target_lang == target_lang)
    query = query.order_by(GlossaryTerm.created_at.desc())

    result = await db.execute(query)
    terms = result.scalars().all()
    return GlossaryTermListResponse(terms=[_to_response(t) for t in terms])


@router.patch("/{term_id}", response_model=GlossaryTermResponse)
async def update_glossary_term(
    term_id: str,
    req: UpdateGlossaryTermRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GlossaryTermResponse:
    result = await db.execute(
        select(GlossaryTerm).where(GlossaryTerm.id == term_id, GlossaryTerm.user_id == user.id)
    )
    term = result.scalar_one_or_none()
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glossary term not found")

    if req.source_lang is not None:
        _validate_lang(req.source_lang, "source_lang")
        term.source_lang = req.source_lang
    if req.target_lang is not None:
        _validate_lang(req.target_lang, "target_lang")
        term.target_lang = req.target_lang
    if req.source_term is not None:
        if not req.source_term.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="source_term cannot be empty"
            )
        term.source_term = req.source_term.strip()
    if req.target_term is not None:
        if not req.target_term.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="target_term cannot be empty"
            )
        term.target_term = req.target_term.strip()
    if req.case_sensitive is not None:
        term.case_sensitive = req.case_sensitive

    await db.commit()
    await db.refresh(term)

    log.info("glossary_term_updated", user_id=str(user.id), term_id=str(term.id))
    return _to_response(term)


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_glossary_term(
    term_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(GlossaryTerm).where(GlossaryTerm.id == term_id, GlossaryTerm.user_id == user.id)
    )
    term = result.scalar_one_or_none()
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glossary term not found")

    await db.delete(term)
    await db.commit()
    log.info("glossary_term_deleted", user_id=str(user.id), term_id=term_id)
