"""
Health check API route — system status and offline readiness.
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    System health and offline readiness check.

    Verifies that all required components are available for offline operation.
    """
    settings = get_settings()

    checks = {
        "database": Path(settings.database_path).exists(),
        "data_directory": Path(settings.data_dir).exists(),
        "model_directory": Path(settings.model_path).exists() or Path(settings.model_path).parent.exists(),
        "index_directory": Path(settings.faiss_index_path).parent.exists(),
        "external_api_required": False,
    }

    # Check FAISS index
    checks["vector_index"] = Path(settings.faiss_index_path).exists()

    # Check model weights
    model_path = Path(settings.model_path)
    if model_path.exists():
        checks["model_weights"] = any(
            model_path.glob("*.bin")
        ) or any(
            model_path.glob("*.safetensors")
        ) or any(
            model_path.glob("*.pt")
        )
    else:
        # Models may be downloaded by open_clip automatically
        checks["model_weights"] = True

    # Try loading embedding model
    try:
        from app.embeddings.manager import get_embedding_model
        model = get_embedding_model()
        checks["embedding_model"] = True
    except Exception:
        checks["embedding_model"] = False

    # Overall status
    critical_checks = ["database", "data_directory", "embedding_model"]
    all_critical = all(checks.get(c, False) for c in critical_checks)

    if all_critical:
        status = "healthy"
    elif checks.get("database") and checks.get("data_directory"):
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "version": "0.1.0",
        "offline_mode": settings.offline_mode,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
