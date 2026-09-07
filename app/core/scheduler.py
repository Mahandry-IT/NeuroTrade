"""Boucle d'analyse continue du bot — pilotée par BotControlService (RG-6).

L'arrêt du scheduler = arrêt immédiat : plus aucune analyse n'est déclenchée.
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,  # Un seul cycle à la fois
                "misfire_grace_time": 30,
            },
        )
    return _scheduler


def start_scheduler(analysis_callback, interval_seconds: int = 60) -> None:
    """Démarre la boucle d'analyse continue."""
    scheduler = get_scheduler()
    if scheduler.running:
        logger.warning("Scheduler déjà en cours d'exécution")
        return

    scheduler.add_job(
        analysis_callback,
        "interval",
        seconds=interval_seconds,
        id="market_analysis_cycle",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler démarré — intervalle %ds", interval_seconds)


def stop_scheduler() -> None:
    """Arrêt immédiat du scheduler (RG-6)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler arrêté immédiatement")
    _scheduler = None


def is_running() -> bool:
    return _scheduler is not None and _scheduler.running
