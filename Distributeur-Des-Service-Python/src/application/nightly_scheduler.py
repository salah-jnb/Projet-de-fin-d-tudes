"""Planification du déclencheur nocturne (webhook n8n par utilisateur)."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.config import settings
from src.infrastructure.safe_console import safe_console_line

_logger = logging.getLogger("koda.nightly_scheduler")
_scheduler: Optional[BackgroundScheduler] = None


def _run_nightly_job(trigger_fn: Callable[[], None]) -> None:
    safe_console_line("[NIGHTLY] Déclencheur 00:00 — lancement du webhook par utilisateur")
    try:
        trigger_fn()
    except Exception:
        _logger.exception("[NIGHTLY] Échec du job nocturne")


def start_nightly_scheduler(trigger_fn: Callable[[], None]) -> None:
    """Démarre le scheduler (cron à l'heure configurée, 00:00 par défaut)."""
    global _scheduler
    if not settings.NIGHTLY_USER_TRIGGER_ENABLED:
        safe_console_line("[NIGHTLY] Déclencheur désactivé (NIGHTLY_USER_TRIGGER_ENABLED=false)")
        return
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_nightly_job,
        trigger=CronTrigger(
            hour=settings.NIGHTLY_TRIGGER_HOUR,
            minute=settings.NIGHTLY_TRIGGER_MINUTE,
        ),
        args=[trigger_fn],
        id="nightly_user_webhook",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    safe_console_line(
        f"[NIGHTLY] Scheduler actif — prochaine exécution chaque jour à "
        f"{settings.NIGHTLY_TRIGGER_HOUR:02d}:{settings.NIGHTLY_TRIGGER_MINUTE:02d}"
    )


def stop_nightly_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        safe_console_line("[NIGHTLY] Scheduler arrêté")


def get_scheduler_status() -> dict:
    job = None
    if _scheduler is not None:
        jobs = _scheduler.get_jobs()
        if jobs:
            job = jobs[0]
    return {
        "enabled": settings.NIGHTLY_USER_TRIGGER_ENABLED,
        "running": _scheduler is not None and _scheduler.running,
        "schedule": f"{settings.NIGHTLY_TRIGGER_HOUR:02d}:{settings.NIGHTLY_TRIGGER_MINUTE:02d}",
        "webhook_url": settings.NIGHTLY_USER_WEBHOOK_URL,
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
    }
