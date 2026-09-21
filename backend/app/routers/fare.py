from fastapi import APIRouter, HTTPException
from app.schemas.fare import CommitRequest, CompareRequest, FareRequest, PreviewRequest
from app.services.taxi_service import PreviewTokenError, TaxiService
router = APIRouter()
@router.post("/fare")
def post_fare(body: FareRequest):
    """只读试算：不签发令牌、不写记录。"""
    with TaxiService() as s:
        return s.fare(body.distance_km, body.slow_min, body.night)
@router.post("/fare/preview")
def post_fare_preview(body: PreviewRequest):
    """只读预览：返回时效令牌与到期时刻，不增加记录条数。"""
    with TaxiService() as s:
        return s.preview_fare(body.distance_km, body.slow_min, body.night, body.trip_id)
@router.post("/fare/commit")
def post_fare_commit(body: CommitRequest):
    """落表：校验令牌时效与预览一致性，一致才写入记录。"""
    try:
        with TaxiService() as s:
            return s.commit_fare(body.token, body.distance_km, body.slow_min, body.night,
                                 body.start, body.mileage, body.slow_fee, body.total, body.trip_id)
    except PreviewTokenError as e:
        raise HTTPException(e.status, e.detail)
@router.post("/compare")
def post_compare(body: CompareRequest):
    with TaxiService() as s:
        return s.compare(body.distance_km, body.slow_min, body.persist)
