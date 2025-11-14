from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal

class QueryItem(BaseModel):
    q: str
    recency_days: Optional[int] = None
    site_filters: Optional[List[str]] = None
    lang: Optional[str] = None
    notes: Optional[str] = None

class SearchPlan(BaseModel):
    queries: List[QueryItem]
    per_query_limit: int = 8

class ReadPick(BaseModel):
    doc_id: str
    reason: Optional[str] = None
    max_tokens: Optional[int] = 2000

class ReadSelection(BaseModel):
    to_read: List[ReadPick]

ControllerAction = Literal["answer", "search", "select_for_read", "stop"]

class ControllerDecision(BaseModel):
    role: Literal["controller_decision"] = "controller_decision"
    decision_id: str
    stage: Literal["initial", "after_read"]
    action: ControllerAction
    direct_answer: Optional[str] = None
    search_plan: Optional[SearchPlan] = None
    read_selection: Optional[ReadSelection] = None
    notes: Optional[List[str]] = None

class SearchDoc(BaseModel):
    doc_id: str
    title: str
    url: HttpUrl
    snippet: Optional[str] = None
    source: Optional[str] = None
    published: Optional[str] = None  # ISO date string

class ReaderReliability(BaseModel):
    rating: float = Field(ge=0.0, le=1.0)
    reasons: str

class ReaderReport(BaseModel):
    role: Literal["reader_report"] = "reader_report"
    doc_id: str
    source_url: HttpUrl
    title: str
    verdict: Literal["supportive", "contradictory", "relevant", "not_relevant"]
    reliability: ReaderReliability
    key_points: List[str] = Field(max_length=6)
    mini_summary: str
    citation: str

class OrchestratorState(BaseModel):
    question: str
    round_index: int = 0
    history_notes: List[str] = []
    search_pool: List[SearchDoc] = []
    reports: List[ReaderReport] = []