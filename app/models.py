from typing import List, Optional
from pydantic import BaseModel, Field


class RawRecord(BaseModel):
    id: str = Field(..., description="Unique record identifier")
    payload: str = Field(..., description="Raw text payload")
    priority: int = Field(default=1, ge=1, le=5, description="Priority from 1 to 5")
    metadata: Optional[dict] = Field(default_factory=dict, description="Arbitrary metadata attributes")


class ProcessBatchRequest(BaseModel):
    batch_id: str = Field(..., description="Identifier for the input batch")
    records: List[RawRecord] = Field(..., min_length=1, description="List of raw records to process")


class ProcessedRecord(BaseModel):
    id: str
    normalized_payload: str
    priority: int
    char_count: int
    word_count: int


class ProcessBatchResponse(BaseModel):
    batch_id: str
    total_received: int
    total_processed: int
    status: str
    downstream_attempts: int
    records: List[ProcessedRecord]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    degraded: bool
