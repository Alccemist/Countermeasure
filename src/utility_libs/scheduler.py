"""
INFORMATION

	This is our scheduler library. All time-related behaviors happen here.
	Our bot interacts with it through cogs/scheduler_cog.py
	
"""

import aiosqlite, asyncio, contextlib, os
from datetime import datetime, date, time, timedelta, timezone 
from dotenv import find_dotenv, load_dotenv
from pathlib import Path
from typing import Awaitable, Callable, Optional
from utility_libs.utilities import SchedulerUtilities, LoggingUtilities

""" [SETUP] """
SchUtil = SchedulerUtilities()
LogUtil = LoggingUtilities(True,True)

ENV = find_dotenv()
if not ENV:
    path = Path(__file__).resolve().parents[1] / "config" / ".env"
load_dotenv(path)

ENV_PATH = find_dotenv()
payout_step:int = int(os.getenv("PAYOUT_STEP"))
RUN_AT_UTC:time = time(int(os.getenv("SCHEDULER_RUNS_UTC")))

LogUtil.print_log(f"Scheduler expected to run every {payout_step} days at UTC <{RUN_AT_UTC}>")

class PayoutScheduler:
	def __init__(self, db:aiosqlite.Connection, announce) -> None:
		self.db:aiosqlite.Connection = db
		# ==> Announce is used to send msgs to a channel. Passed in by the cog.
		self.announce:Callable[[str], Awaitable[None]] = announce
		self._task: Optional[asyncio.Task] = None

	""" [DEBUG BLOCK] """
	def is_ready(self) -> bool:
		if self.db:
			LogUtil.print_debug(f"SCHEDULER FOR DATABASE {self.db} READY...")
			return True
		else:
			LogUtil.print_debug(f"SCHEDULER NOT READY: MISSING DATABASE")
			return False


	""" [TASK LIFECYCLE BLOCK] """
	async def start(self):
		await self.backfill_to_today()
		self._task = asyncio.create_task(self._tick_forever())

	async def stop(self):
		if self._task:
			self._task.cancel()
			with contextlib.suppress(asyncio.CancelledError):
				# ==> Used when stopping a background task. Swallows the error.
				await self._task
			self._task = None
	
	""" [BOOTSTRAP BLOCK] """
	# ==> Ngl. Just took this from data_handler. No need to make a function for creating only the schedule table
	async def _ensure_tables(self) -> None:
		await self.db.execute("""
			CREATE TABLE IF NOT EXISTS schedule(
				run_date TEXT PRIMARY KEY,
				status TEXT NOT NULL CHECK(status IN ('started','complete','failed')),
				started_at TEXT NOT NULL, -- datetime('now')
				finished_at TEXT, -- set when completed OR failed
				error_msg TEXT -- Optional failure note				
			)
		""")
		await self.db.commit()

	""" [TIME SCHEDULING BLOCK] """
	def today_utc(self) -> date:
		print(f"[DEBUG]: Getting today_utc: {datetime.now(timezone.utc).date()}")
		return datetime.now(timezone.utc).date()
	
	def seconds_until_next_run(self) -> float:
		# ==> This gives us the seconds
		now = datetime.now(timezone.utc)
		LogUtil.print_debug(f"Getting now: {now}")
		today_target = datetime.combine(now.date(), RUN_AT_UTC, tzinfo=timezone.utc)
		LogUtil.print_debug(f"Getting today_target: {today_target}")
			# ==> Combines today's date with our desired runtime using a utc timezone.
		if now <= today_target:
			next_run = today_target
			LogUtil.print_debug(f"Expecting payout today <{today_target}>")
		else:
			next_run = today_target + timedelta(days=payout_step) 
			LogUtil.print_debug(f"Expecting payout later: <{next_run}>")
		return (next_run - now).total_seconds()

	async def _tick_forever(self):
		while True:
			target_date:date = self.today_utc()
			await self.payout_for_day(target_date)
			LogUtil.print_debug(f"Fetched target date, called payout_for_day({target_date})")
			await asyncio.sleep(self.seconds_until_next_run())
			LogUtil.print_debug(f"Sleeping for {self.seconds_until_next_run()} s")

	""" [PAYOUT BLOCK] """
	async def payout_for_day(self, d:date) -> None:
		run_date = d.isoformat()
		LogUtil.print_debug(f"Fetched run_date: {run_date}... STARTING PAYOUT")
		# Let's try to claim this date. BEGIN IMMEDIATE helps us avoid race conditions.
		await self.db.execute("BEGIN IMMEDIATE")
		try:
			# ==> Inside our schedule table, create a new run date.
			c = await self.db.execute(
				"""INSERT OR IGNORE INTO schedule(run_date, status, started_at)
				VALUES (?, 'started', datetime('now'))""", (run_date,)
			)
			inserted = c.rowcount and c.rowcount > 0
			LogUtil.print_debug(f"Fetched amount inserted: {inserted}")
			if not inserted:
				# ==> Date already exists. Check its status instead.
				async with self.db.execute(
					"""SELECT status FROM schedule WHERE run_date = ?""", (run_date,)
				) as c2:
					status_row = await c2.fetchone()
				status = status_row[0] if status_row else None
				if status == 'complete':
					LogUtil.print_debug(f"{run_date} Already done. Rolling back...")
					await self.db.rollback(); return
				# If 'failed' or 'started', we should retry. The latter implies a hang...

			# [PAY EVERYBODY ==> sourcing user_economy, user_tech tables]
			# Using a CTE instead of a view for durability. Schema changes won't update a VIEW IF NOT EXISTS.
			# ==> UNION ALL stacks our two selects on top of each other. UNION removes duplicates, which is unnecessary work.
			# ==> agg is our aggregation of incomes. This is used to credit players.
			# ==> We finally execute update in the same block so the CTE can be accessed.
			LogUtil.print_debug(f"Executing CTE and UPDATE...")
			await self.db.execute(
				""" WITH v AS (
						SELECT user_id, SUM(COALESCE(economy_income, 0)) AS cr,	0 AS rp
						FROM user_economy GROUP BY user_id
						UNION ALL
						SELECT user_id, 0 AS cr, SUM(COALESCE(tech_income, 0)) AS rp
						FROM user_tech GROUP BY user_id
					),
					agg AS (
						SELECT user_id, SUM(cr) AS cr, SUM(rp) AS rp
						FROM v GROUP BY user_id
					)

					UPDATE users AS u
					SET balance = balance
						+ COALESCE((SELECT a.cr FROM agg a WHERE a.user_id = u.user_id), 0),
						research = research
						+ COALESCE((SELECT a.rp FROM agg a WHERE a.user_id = u.user_id), 0)
					WHERE EXISTS (SELECT 1 FROM agg a WHERE a.user_id = u.user_id);
				"""
			)	# ==> Since we have a scalar subquery, if we're missing a row, we'll get NULL. We coalesce again to avoid NULLs.
			# ==> WHERE EXISTS is a safeguard, so we're only affecting users involved in a payout aggregation.
			
			# If we've made it to here, we've definitely succeeded!
			await self.db.execute(
				"UPDATE schedule SET status='complete', finished_at=datetime('now') WHERE run_date=?",
				(run_date,)
			)
			await self.db.commit()
			await self.announce(f"```<{datetime.now(timezone.utc).date()}: {datetime.now(timezone.utc).time()}> PAYOUT ISSUED ```")
			LogUtil.print_debug(f"PAYOUT FOR {run_date} COMMITTED")

		# If the payout fails...
		except Exception as e:
			await self.db.rollback()
			await self.db.execute("BEGIN IMMEDIATE")
			await self.db.execute(
				"""INSERT OR IGNORE INTO schedule(run_date, status, started_at)
				VALUES (?, 'started', datetime('now'))""", (run_date,)
			)
			await self.db.execute(
				"UPDATE schedule SET status='failed', finished_at=datetime('now'), error_msg=? WHERE run_date = ?",
				(f"{type(e).__name__}: {e}", run_date)
			)
			await self.db.commit()
			# Announce failure
			await self.announce(f"[ERR]: Payout for {run_date} failed: {type(e).__name__}: {e}")
			LogUtil.print_debug(f"[DEBUG]: Payout failed: {type(e).__name__}: {e}")
			# ==> type(e) gets our error type (error types are objs)

	""" [BACKFILLING BLOCK] """
	async def backfill_to_today(self) -> None:
		LogUtil.print_debug("Called backfill_to_today")
		today = self.today_utc()
		async with self.db.execute(
			"SELECT MAX(run_date) FROM schedule WHERE status='complete'"
		) as cur: # ==> Selecting MAX(run_date) means selecting the most recent date.
			row = await cur.fetchone()
		LogUtil.print_debug(f"Fetched backfill row: {row[0]}")

		if row and row[0]:
			last_complete = SchUtil.parse_date(row[0])
			LogUtil.print_debug(f"Fetched date for row: {SchUtil.parse_date(row[0])}")
		else:
			last_complete = None

		if last_complete:
			d = last_complete + timedelta(days=1)
		else:
			d = today - timedelta(days=1) # ==> Subtracting time means moving back.

		while d < today:
			LogUtil.print_debug(f"Backfilling for day {d}")
			await self.payout_for_day(d)
			d += timedelta(days=1) # ==> Advance to the next day for backfilling...