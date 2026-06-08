"""
Endpoints du bilan santé (propose-only). Le frontend interroge /insights et peut
forcer un /check. Aucune action n'est exécutée ici — les commandes suggérées sont
renvoyées telles quelles, à l'utilisateur de décider.
"""
from fastapi import APIRouter

from services import health_monitor

router = APIRouter()


@router.get("/insights")
def insights():
    """Dernier bilan santé (constats + actions SUGGÉRÉES)."""
    return health_monitor.get_state()


@router.post("/check")
async def check_now():
    """Force un bilan immédiat (read-only)."""
    import asyncio
    return await asyncio.to_thread(health_monitor.run_checks)
