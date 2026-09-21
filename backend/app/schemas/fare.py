from pydantic import BaseModel, Field

class FarePreviewRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    night: bool = False
    trip_id: int | None = None

class FareCommitRequest(BaseModel):
    token: str
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    night: bool = False
    start: float = Field(ge=0)
    mileage: float = Field(ge=0)
    slow_fee: float = Field(ge=0)
    total: float = Field(ge=0)

class FareQuoteRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    night: bool = False

class CompareRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    persist: bool = False
