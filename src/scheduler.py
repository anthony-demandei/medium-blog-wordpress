from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
import pytz
from typing import Callable

logger = logging.getLogger(__name__)

class SyncScheduler:
    def __init__(self, timezone: str = 'America/Sao_Paulo'):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(timezone)
        self.sync_function = None
    
    def set_sync_function(self, func: Callable):
        """Set the function to be called during sync"""
        self.sync_function = func
    
    def schedule_daily_sync(self, hour: int = 9, minute: int = 0):
        """Schedule daily sync at specific time"""
        if not self.sync_function:
            logger.error("Sync function not set. Use set_sync_function() first.")
            return
        
        # Remove existing job if any
        if self.scheduler.get_job('daily_sync'):
            self.scheduler.remove_job('daily_sync')
        
        # Create cron trigger
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=self.timezone
        )
        
        # Add job
        self.scheduler.add_job(
            func=self._run_sync,
            trigger=trigger,
            id='daily_sync',
            name='Daily Medium to WordPress Sync',
            replace_existing=True
        )
        
        logger.info(f"Daily sync scheduled at {hour:02d}:{minute:02d} {self.timezone}")
    
    def schedule_immediate_sync(self):
        """Schedule an immediate sync (useful for testing)"""
        if not self.sync_function:
            logger.error("Sync function not set. Use set_sync_function() first.")
            return
        
        self.scheduler.add_job(
            func=self._run_sync,
            id='immediate_sync',
            name='Immediate Sync',
            replace_existing=True
        )
        
        logger.info("Immediate sync scheduled")
    
    def _run_sync(self):
        """Wrapper to run sync with error handling"""
        try:
            logger.info(f"Starting scheduled sync at {datetime.now()}")
            if self.sync_function:
                result = self.sync_function()
                logger.info(f"Sync completed: {result}")
            else:
                logger.error("No sync function configured")
        except Exception as e:
            logger.error(f"Error during scheduled sync: {e}")
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def get_next_run_time(self) -> str:
        """Get next scheduled run time"""
        job = self.scheduler.get_job('daily_sync')
        if job and job.next_run_time:
            return job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        return "No sync scheduled"
    
    def get_jobs(self) -> list:
        """Get all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def reschedule_sync(self, hour: int, minute: int):
        """Reschedule the daily sync"""
        self.schedule_daily_sync(hour, minute)
    
    def pause_sync(self):
        """Pause the daily sync"""
        job = self.scheduler.get_job('daily_sync')
        if job:
            job.pause()
            logger.info("Daily sync paused")
    
    def resume_sync(self):
        """Resume the daily sync"""
        job = self.scheduler.get_job('daily_sync')
        if job:
            job.resume()
            logger.info("Daily sync resumed")