from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GuidanceDetail(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    problem: str = ''
    action: str = ''
    rationale: str = ''
    tech_context: str | list = ''
    examples: list[str] = Field(default_factory=list)
    check_codes: list[str] = Field(default_factory=list)


class KnowledgeRecord(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    kid: str
    type: Literal['FACT', 'STANDARD', 'FINDING', 'UNCERTAINTY', 'GUIDANCE']
    scope: str | None = None
    statement: str
    context: str | None = None
    status: Literal['active', 'contested', 'deprecated', 'archived'] = 'active'
    confidence: Literal['high', 'medium', 'low'] = 'medium'
    support: str = 'partial'
    aeog_phases: list[str] = Field(default_factory=list)
    check_links: list[dict] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    uncertainty: str | None = None
    contradiction: str | None = None
    guidance: GuidanceDetail | None = None
    relationships: list[dict] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)
    history: list | dict = Field(default_factory=list)
    priority_score: int | None = None


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    eid: str
    kid: str
    sid: str
    relationship: str = 'supports'
    weight: str = 'primary'
    note: str = ''


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    sid: str
    url: str | None = None
    title: str | None = 'Untitled'
    publisher: str | None = None
    authority: str = 'T3'
    pub_date: str | None = None
    excerpt: str | None = None
    notes: str | None = None


class CheckCodeMapping(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    check_code: str
    kid: str
    priority_score: int = 10


class Resolution(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    path: Literal['DETERMINISTIC', 'SEMANTIC', 'INSUFFICIENT', 'DEPRECATED']
    primary_kid: str | None = None
    primary_record: KnowledgeRecord | None = None
    guidance: GuidanceDetail | None = None
    backing_facts: list[KnowledgeRecord] = Field(default_factory=list)
    evidence_chain: list[EvidenceRecord] = Field(default_factory=list)
    source_citations: list[SourceRecord] = Field(default_factory=list)
    enrichment: list[dict] = Field(default_factory=list)
    priority_score: int = 10
    is_contested: bool = False
    contested_reason: str | None = None
    is_stale: bool = False
    stale_since: str | None = None
    rag_available: bool = False
    confidence_score: float | None = None
