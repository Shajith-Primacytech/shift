"""Shared capture validation; AI output is evidence selection, never maintenance advice."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class SubmissionFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    machineId: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=140)
    symptom: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=10, max_length=8000)
    kind: Literal["SOP", "Field note", "Resolution"] = "Field note"
    problem: str = Field(default="", max_length=8000)
    rootCause: str = Field(default="", max_length=8000)
    resolution: str = Field(default="", max_length=8000)
    safetyNotes: str = Field(default="", max_length=8000)


SourceField = Literal[
    "machineId",
    "title",
    "symptom",
    "content",
    "problem",
    "rootCause",
    "resolution",
    "safetyNotes",
]


class SourceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: SourceField
    quote: str = Field(min_length=1, max_length=1200)


Quotes = Annotated[list[SourceQuote], Field(max_length=5)]


class ProposedStructure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    machineContext: Quotes
    reportedSymptoms: Quotes
    faultCodes: Quotes
    operatingConditions: Quotes
    observations: Quotes
    confirmedRootCause: Quotes
    actionsPerformed: Quotes
    observedOutcome: Quotes
    verificationSteps: Quotes
    safetyConsiderations: Quotes


class ReviewedStructure(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    machineContext: str = Field(max_length=1600)
    reportedSymptoms: str = Field(max_length=1600)
    faultCodes: str = Field(max_length=1600)
    operatingConditions: str = Field(max_length=1600)
    observations: str = Field(max_length=1600)
    confirmedRootCause: str = Field(max_length=1600)
    actionsPerformed: str = Field(max_length=1600)
    observedOutcome: str = Field(max_length=1600)
    verificationSteps: str = Field(max_length=1600)
    safetyConsiderations: str = Field(max_length=1600)


class AIReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runId: str = Field(min_length=1, max_length=64)
    fields: ReviewedStructure
    reviewed: Literal[True]


class Submission(SubmissionFields):
    aiReview: AIReview | None = None


def mapped_submission(
    source: SubmissionFields, fields: ReviewedStructure
) -> SubmissionFields:
    """Fit the reviewed ten categories into existing indexed knowledge columns."""

    def section(label, value):
        return f"{label}: {value}" if value else ""

    data = source.model_dump()
    data.update(
        problem="\n\n".join(
            filter(
                None,
                [
                    "AI-assisted organization, reviewed by technician; supervisor verification required.",
                    section("Machine/equipment context", fields.machineContext),
                    section("Reported symptoms", fields.reportedSymptoms),
                    section("Fault codes supplied", fields.faultCodes),
                    section("Operating conditions", fields.operatingConditions),
                    section("Technician observations", fields.observations),
                ],
            )
        ),
        rootCause=section(
            "Technician-reported confirmed root cause (not independently verified)",
            fields.confirmedRootCause,
        ),
        resolution="\n\n".join(
            filter(
                None,
                [
                    section("Actions performed", fields.actionsPerformed),
                    section("Observed outcome", fields.observedOutcome),
                    section("Verification steps reported", fields.verificationSteps),
                ],
            )
        ),
        safetyNotes=fields.safetyConsiderations,
    )
    return SubmissionFields.model_validate(data)
