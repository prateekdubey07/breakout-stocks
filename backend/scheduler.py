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

    async def _auto_scan():
        import asyncio
        import json
        from concurrent.futures import ThreadPoolExecutor
        from database import get_conn
        from scoring.bps_engine import score_ticker
        from models import BpsResult

        conn = get_conn()
        tickers = [r[0] for r in conn.execute("SELECT ticker FROM default_tickers ORDER BY ticker").fetchall()]
        conn.close()
        if not tickers:
            return

        loop = asyncio.get_event_loop()
        ex = ThreadPoolExecutor(max_workers=8)
        try:
            results = await asyncio.gather(*[loop.run_in_executor(ex, score_ticker, t) for t in tickers])
        finally:
            ex.shutdown(wait=False)

        candidates = [r for r in results if r.breakout_probability_score >= 50]
        candidates.sort(key=lambda x: x.breakout_probability_score, reverse=True)

        conn = get_conn()
        conn.execute(
            "INSERT INTO scan_results (tickers_json, results_json, trigger) VALUES (?,?,?)",
            (json.dumps(tickers),
             json.dumps([c.dict() if hasattr(c, 'dict') else c for c in candidates]),
             "auto")
        )
        conn.execute("DELETE FROM scan_results WHERE id NOT IN (SELECT id FROM scan_results ORDER BY id DESC LIMIT 50)")
        conn.commit()
        conn.close()

        high = [c for c in candidates if c.conviction == "HIGH"]
        if high:
            await manager.broadcast({"type": "auto_scan", "high_conviction": len(high), "top": high[0].ticker if high else None})

    # Mon-Fri 9:00-15:45 ET every 15 mins (covers market open at 9:30)
    try:
        scheduler.add_job(
            _auto_scan, "cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="0,15,30,45",
            timezone="America/New_York",
            id="auto_scan",
            replace_existing=True
        )
    except Exception:
        pass

    try:
        from ml.trainer import train_all
        scheduler.add_job(train_all, "cron", day_of_week="sun", hour=2, minute=0,
                          id="weekly_retrain", replace_existing=True)
    except Exception:
        pass
