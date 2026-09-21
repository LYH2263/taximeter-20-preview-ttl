from pydantic import BaseModel, Field

class FareRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    night: bool = False

class PreviewRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    night: bool = False
    trip_id: int | None = None

class CommitRequest(BaseModel):
    token: str
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    night: bool = False
    start: float
    mileage: float
    slow_fee: float
    total: float
    trip_id: int | None = None

class CompareRequest(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)
    persist: bool = False
