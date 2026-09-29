from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    notes: str | None = Field(default=None, max_length=4000)
    claims: dict[str, str] = Field(default_factory=dict)


class CasePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    notes: str | None = Field(default=None, max_length=4000)
    claims: dict[str, str] | None = None


class ClaimCreate(BaseModel):
    field: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=2000)


class ManualEvidenceCreate(BaseModel):
    field: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=2000)
    source_name: str = Field(min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=4000)


class EntityResolutionRequest(BaseModel):
    submitted: dict[str, str]
    observed: dict[str, str]
