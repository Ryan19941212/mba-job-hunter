"""
Metrics API Router

Provides Prometheus-compatible metrics endpoint for monitoring application health and performance.
"""

from fastapi import APIRouter, Response
from app.utils.metrics import metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns application metrics in Prometheus format for scraping by monitoring systems.
    """
    metrics_data = metrics.get_metrics()
    return Response(content=metrics_data, media_type="text/plain")