from fastapi import APIRouter, HTTPException
from app.schemas.fare import CompareRequest, FareCommitRequest, FarePreviewRequest, FareQuoteRequest
from app.services.taxi_service import FareTokenError, TaxiService
router = APIRouter()
@router.post("/fare/preview")
def post_fare_preview(body: FarePreviewRequest):
    with TaxiService() as s:
        return s.preview_fare(body.distance_km, body.slow_min, body.night, body.trip_id)
@router.post("/fare/commit")
def post_fare_commit(body: FareCommitRequest):
    with TaxiService() as s:
        try:
            return s.commit_fare(body.token, body.distance_km, body.slow_min, body.night,
                                 body.start, body.mileage, body.slow_fee, body.total)
        except FareTokenError as e:
            raise HTTPException(status_code=409, detail=str(e))
@router.post("/fare/quote")
def post_fare_quote(body: FareQuoteRequest):
    with TaxiService() as s:
        return s.quote_fare(body.distance_km, body.slow_min, body.night)
@router.post("/compare")
def post_compare(body: CompareRequest):
    with TaxiService() as s:
        return s.compare(body.distance_km, body.slow_min, body.persist)
