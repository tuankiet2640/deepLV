"""Glossary term management router.

Lets a user define forced source-term -> target-term overrides scoped to a
(source_lang, target_lang) pair. Applied automatically whenever that user
translates that pair (see src/api/services/glossary.py for the
substitution mechanism) -- no per-translation selection needed.
"""

import csv
import io
import json

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database import get_db
from src.api.middleware.dependencies import get_current_user
from src.api.models.glossary_term import GlossaryTerm
from src.api.models.user import User
from src.api.services.glossary import MAX_TERMS_PER_USER
from src.api.services.language_detect import SUPPORTED_LANGUAGES

GLOSSARY_EXPORT_FIELDS = [
    "source_lang",
    "target_lang",
    "source_term",
    "target_term",
    "case_sensitive",
    "category",
    "notes",
]

log = structlog.get_logger()
router = APIRouter(prefix="/glossary", tags=["glossary"])


class GlossaryTermRequest(BaseModel):
    source_lang: str
    target_lang: str
    source_term: str
    target_term: str
    case_sensitive: bool = False
    category: str | None = None
    notes: str | None = None


class UpdateGlossaryTermRequest(BaseModel):
    source_lang: str | None = None
    target_lang: str | None = None
    source_term: str | None = None
    target_term: str | None = None
    case_sensitive: bool | None = None
    category: str | None = None
    notes: str | None = None


class GlossaryTermResponse(BaseModel):
    id: str
    source_lang: str
    target_lang: str
    source_term: str
    target_term: str
    case_sensitive: bool
    category: str | None
    notes: str | None
    created_at: str


class GlossaryTermListResponse(BaseModel):
    terms: list[GlossaryTermResponse]


class GlossaryImportResponse(BaseModel):
    created: int
    skipped_duplicate: int
    skipped_cap: int
    errors: list[dict[str, str | int]]


def _to_response(term: GlossaryTerm) -> GlossaryTermResponse:
    return GlossaryTermResponse(
        id=str(term.id),
        source_lang=term.source_lang,
        target_lang=term.target_lang,
        source_term=term.source_term,
        target_term=term.target_term,
        case_sensitive=term.case_sensitive,
        category=term.category,
        notes=term.notes,
        created_at=term.created_at.isoformat(),
    )


def _validate_lang(lang: str, field: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported {field}: {lang}",
        )


def _is_valid_lang(lang: str) -> bool:
    return lang in SUPPORTED_LANGUAGES


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
        category=req.category.strip() if req.category else None,
        notes=req.notes.strip() if req.notes else None,
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


@router.get("/export")
async def export_glossary_terms(
    format: str = Query(default="json", pattern=r"^(json|csv)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export the user's glossary so it can be shared and re-imported into
    another account (e.g. a Legal team member sharing their terminology
    with Marketing) without needing a team/organization concept."""
    result = await db.execute(
        select(GlossaryTerm)
        .where(GlossaryTerm.user_id == user.id)
        .order_by(GlossaryTerm.created_at.asc())
    )
    terms = result.scalars().all()
    rows = [
        {
            "source_lang": t.source_lang,
            "target_lang": t.target_lang,
            "source_term": t.source_term,
            "target_term": t.target_term,
            "case_sensitive": t.case_sensitive,
            "category": t.category or "",
            "notes": t.notes or "",
        }
        for t in terms
    ]

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=GLOSSARY_EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        content = buffer.getvalue()
        media_type = "text/csv"
        filename = "glossary.csv"
    else:
        content = json.dumps(rows, indent=2)
        media_type = "application/json"
        filename = "glossary.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import", response_model=GlossaryImportResponse)
async def import_glossary_terms(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GlossaryImportResponse:
    """Bulk-import glossary terms from a previously exported JSON or CSV
    file. Partial success: a bad row is skipped and reported, not treated
    as a reason to fail the whole batch."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must have a filename"
        )

    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in ("json", "csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Upload a .json or .csv file.",
        )

    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is not valid UTF-8"
        )

    try:
        if extension == "json":
            rows = json.loads(raw_text)
            if not isinstance(rows, list):
                raise ValueError("JSON glossary export must be an array of term objects")
        else:
            rows = list(csv.DictReader(io.StringIO(raw_text)))
    except (json.JSONDecodeError, ValueError, csv.Error) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse file: {e}"
        )

    # Fetch existing terms once (avoid an N+1 query per row) and build a
    # de-dup key set covering both pre-existing rows and duplicates within
    # this same uploaded file.
    existing_result = await db.execute(select(GlossaryTerm).where(GlossaryTerm.user_id == user.id))
    existing_count = 0
    seen: set[tuple[str, str, str]] = set()
    for t in existing_result.scalars():
        existing_count += 1
        seen.add((t.source_lang, t.target_lang, t.source_term.strip().lower()))

    created = 0
    skipped_duplicate = 0
    skipped_cap = 0
    errors: list[dict[str, str | int]] = []
    staged: list[GlossaryTerm] = []

    for index, row in enumerate(rows):
        source_lang = str(row.get("source_lang", "")).strip()
        target_lang = str(row.get("target_lang", "")).strip()
        source_term = str(row.get("source_term", "")).strip()
        target_term = str(row.get("target_term", "")).strip()
        case_sensitive_raw = row.get("case_sensitive", False)
        case_sensitive = (
            case_sensitive_raw
            if isinstance(case_sensitive_raw, bool)
            else str(case_sensitive_raw).strip().lower() in ("true", "1", "yes")
        )
        category = str(row.get("category") or "").strip() or None
        notes = str(row.get("notes") or "").strip() or None

        if not source_term or not target_term:
            errors.append({"row": index, "message": "source_term and target_term cannot be empty"})
            continue
        if not _is_valid_lang(source_lang):
            errors.append({"row": index, "message": f"Unsupported source_lang: {source_lang}"})
            continue
        if not _is_valid_lang(target_lang):
            errors.append({"row": index, "message": f"Unsupported target_lang: {target_lang}"})
            continue

        key = (source_lang, target_lang, source_term.lower())
        if key in seen:
            skipped_duplicate += 1
            continue

        if existing_count + len(staged) >= MAX_TERMS_PER_USER:
            skipped_cap += 1
            continue

        seen.add(key)
        staged.append(
            GlossaryTerm(
                user_id=user.id,
                source_lang=source_lang,
                target_lang=target_lang,
                source_term=source_term,
                target_term=target_term,
                case_sensitive=case_sensitive,
                category=category,
                notes=notes,
            )
        )
        created += 1

    if staged:
        db.add_all(staged)
        await db.commit()

    log.info(
        "glossary_terms_imported",
        user_id=str(user.id),
        created=created,
        skipped_duplicate=skipped_duplicate,
        skipped_cap=skipped_cap,
        errors=len(errors),
    )
    return GlossaryImportResponse(
        created=created,
        skipped_duplicate=skipped_duplicate,
        skipped_cap=skipped_cap,
        errors=errors,
    )


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
    if req.category is not None:
        term.category = req.category.strip() or None
    if req.notes is not None:
        term.notes = req.notes.strip() or None

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
