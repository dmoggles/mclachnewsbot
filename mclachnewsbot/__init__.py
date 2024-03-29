from dagster import (
    Definitions,
    load_assets_from_modules,
    define_asset_job,
    AssetSelection,
    ScheduleDefinition,
)
from . import config

from . import assets

config = config.parse_config()

all_assets = load_assets_from_modules([assets])

jobs = [
    define_asset_job(
        f"{topic}_job",
        selection=AssetSelection.all(),
        config={"ops": {"get_news_stories": {"config": {"topic_name": topic}}}},
    )
    for topic in config["settings"]
]

schedules = [
    ScheduleDefinition(
        cron_schedule="0,5,10,15,20,25,30,35,40,45,50,55 * * * *",
        job=job,
    )
    for job in jobs
]

defs = Definitions(assets=all_assets, jobs=jobs, schedules=schedules)
