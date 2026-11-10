"""Case reply contracts and validation. Provider claims remain unverified."""
import base64
import binascii
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated

CleanText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
FILE_LIMIT = 512 * 1024


class ChecklistItem(BaseModel):
    label: CleanText
    priority: Literal["MUST", "NICE"]


class CaseOutreachIn(BaseModel):
    facility_id: str = Field(min_length=1, max_length=64)
    consent: Literal[True]
    summary: str = Field(min_length=1, max_length=1200)
    items: list[ChecklistItem] = Field(max_length=60)
    intent: Literal["visit", "pricing"]
    preferred_date: str | None = Field(default=None, max_length=10)


class ReplyFile(BaseModel):
    name: CleanText
    content: str = Field(min_length=4, max_length=4 * ((FILE_LIMIT + 2) // 3))


class CaseReplyIn(BaseModel):
    answers: dict[int, Literal["yes", "no", "depends"]] = Field(default_factory=dict, max_length=60)
    availability: Literal["available", "waitlist", "unavailable", "unknown"] | None = None
    monthly_price_cents: int | None = Field(default=None, gt=0, le=100_000_000)
    notes: str = Field(default="", max_length=2000)
    files: list[ReplyFile] = Field(default_factory=list, max_length=2)


def can_view(outreach, now=None):
    if outreach.status not in {"SENT", "RESPONDED"} or not outreach.sent_at:
        return False
    sent = outreach.sent_at
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    return sent <= (now or datetime.now(timezone.utc)) < sent + timedelta(days=14)


def validated_reply(reply: CaseReplyIn, snapshot: dict) -> dict:
    if not all(0 <= key < len(snapshot["items"]) for key in reply.answers):
        raise ValueError("Unknown checklist item")
    if not any((reply.answers, reply.availability, reply.monthly_price_cents, reply.notes.strip(), reply.files)):
        raise ValueError("Answer at least one item or add a note or file.")
    files = []
    for file in reply.files:
        try:
            content = base64.b64decode(file.content, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid attachment") from exc
        if len(content) > FILE_LIMIT or not content.startswith((b"%PDF-", b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")):
            raise ValueError("Attach a PDF, PNG or JPEG of up to 512 KB.")
        files.append({"name": file.name, "content": file.content})
    must = [i for i, item in enumerate(snapshot["items"]) if item["priority"] == "MUST"]
    care_status = (
        "DOES_NOT_MEET_REQUIRED_NEED" if any(reply.answers.get(i) == "no" for i in must)
        else "NEEDS_FOLLOW_UP" if not must or any(reply.answers.get(i) != "yes" for i in must)
        else "FACILITY_REPORTED_REQUIRED_NEEDS_MET"
    )
    return {**reply.model_dump(exclude={"files"}), "files": files, "care_status": care_status,
            "evidence_status": "FACILITY_REPORTED"}
