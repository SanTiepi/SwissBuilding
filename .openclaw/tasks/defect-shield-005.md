# Task: DefectShield — Lettre PDF Gotenberg

## Commit message
feat(defect-shield): generate notification letter PDF via Gotenberg

## What to do
Wire the existing defect_letter_service (which generates HTML notification letters in FR/DE/IT) into a new or updated API endpoint that converts HTML→PDF via Gotenberg. The endpoint accepts timeline_id + language (fr/de/it) and returns a binary PDF file with formal defect notification (Art. 367 CO), building address, EGID, defect type, discovery date, deadline, legal text, and signature blocks.

## Files to modify
- `backend/app/api/defect_timeline.py` (update POST /defects/{timeline_id}/generate-letter endpoint to return PDF bytes + Content-Disposition header)
- `backend/app/services/defect_letter_service.py` (verify generate_letter_html() exists and is complete)
- `backend/tests/test_defect_letter.py` (add test for PDF generation via endpoint; validate PDF contains expected text)

## Existing patterns to follow

From `defect_letter_service.py`:
```python
async def generate_letter_html(
    db: AsyncSession, timeline_id: UUID, lang: Literal["fr", "de", "it"]
) -> str:
    """Generate HTML notification letter with building + defect + legal info."""
    # Returns HTML string with i18n content

async def generate_letter_pdf(
    db: AsyncSession, timeline_id: UUID, lang: Literal["fr", "de", "it"] = "fr"
) -> bytes:
    """Convert HTML to PDF via Gotenberg."""
    html = await generate_letter_html(db, timeline_id, lang)
    pdf_bytes = await html_to_pdf(html, margin_mm=15)
    return pdf_bytes
```

From existing Gotenberg pattern (other services):
```python
from app.services.gotenberg_service import html_to_pdf

pdf_bytes = await html_to_pdf(html_content, margin_mm=20)
return Response(
    content=pdf_bytes,
    media_type="application/pdf",
    headers={"Content-Disposition": f'attachment; filename="defect-notification-{id}.pdf"'}
)
```

## Acceptance criteria
- [ ] Endpoint accepts timeline_id + language (default fr)
- [ ] Returns binary PDF (Content-Type: application/pdf)
- [ ] PDF includes: building address, EGID, defect type, discovery date, deadline, legal text (Art. 367 CO), signature blocks
- [ ] PDF available in FR/DE/IT (tested with all 3)
- [ ] Error handling for missing timeline or Gotenberg failure
- [ ] Tests pass (PDF generation + content validation)
- [ ] Existing tests still pass (no regression)

## Test command
cd backend && python -m pytest tests/test_defect_letter.py -v

## Rules
- Do NOT modify files outside the list above
- Do NOT push
- Use existing Gotenberg service (no new dependencies)
- Commit with the message above if tests pass
