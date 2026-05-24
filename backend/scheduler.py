from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def setup_scheduler():
    from websocket.manager import manager
    from watchlist.monitor import run_watchlist_scan

    async def _poll():
        alerts = run_watchlist_scan()
        changed = [a for a in alerts if a["status"] in ("TRIGGERED", "BREAKING_DOWN", "STOPPED_OUT")]
        if changed:
            await manager.broadcast({"type": "watchlist_update", "alerts": changed})

    scheduler.add_job(_poll, "interval", seconds=60, id="watchlist_poll", replace_existing=True)

    try:
        from ml.trainer import train_all
        scheduler.add_job(train_all, "cron", day_of_week="sun", hour=2, minute=0,
                          id="weekly_retrain", replace_existing=True)
    except Exception:
        pass
