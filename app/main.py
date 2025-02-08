#! /usr/bin/env python3
import asyncio
import os
import sys
from loguru import logger
from typing import Any, List

from DataManager import DataManager
from fastapi import Body, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi_versioning import VersionedFastAPI, version
from loguru import logger
from uvicorn import Config, Server

SERVICE_NAME = "slam"

app = FastAPI(
    title="SLAM",
    description="SLAM service.",
    debug=True,
)

logger.info(f"Starting {SERVICE_NAME}")
data_manager = DataManager()


@app.get("/gps")
@version(1, 0)
def get_gps_data() -> Any:
    logger.debug("Fetching GPS data.")
    return data_manager.get_gps_data()


@app.get("/imu")
@version(1, 0)
def get_gps_data() -> Any:
    logger.debug("Fetching IMU data.")
    return data_manager.get_imu_data()


@app.get("/attitude")
@version(1, 0)
def get_gps_data() -> Any:
    logger.debug("Fetching attitude data.")
    return data_manager.get_attitude_data()


app = VersionedFastAPI(
    app,
    version="1.0.0",
    prefix_format="/v{major}.{minor}",
    enable_latest=True,
)

app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
async def root() -> HTMLResponse:
    return HTMLResponse(content="index.html", status_code=200)

if __name__ == "__main__":
    logger.debug("Starting SLAM.")
    if os.geteuid() != 0:
        logger.error(
            "You need root privileges to run this script.\nPlease try again, this time using **sudo**. Exiting."
        )
        sys.exit(1)

    loop = asyncio.new_event_loop()

    # Running uvicorn with log disabled so loguru can handle it
    config = Config(app=app, loop=loop, host="0.0.0.0",
                    port=9050, log_config=None)
    server = Server(config)

    loop.run_until_complete(server.serve())
