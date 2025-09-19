from celery import shared_task
from . import utils  # Your existing scraping functions

@shared_task
def run_scraper_task(query):
    """A Celery task to run the full scraping pipeline."""
    return utils.run_pipeline_for_query(query)