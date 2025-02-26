#! /usr/bin/env python3
from matplotlib import pyplot as plt
import io
from fastapi.responses import StreamingResponse
import asyncio
import os
import sys
import numpy as np
from loguru import logger
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi_versioning import VersionedFastAPI, version
from loguru import logger
from Processor import Processor
from ping.PingManager import PingManager
from uvicorn import Config, Server

from settings import *

SERVICE_NAME = "slam"

app = FastAPI(
    title="SLAM",
    description="SLAM service.",
    debug=True,
)

logger.info(f"Starting {SERVICE_NAME}")
data_processor = Processor()
ping_manager = PingManager(device=None, baudrate=115200, udp=UDP_PORT)


@app.post("/start_recording")
@version(1, 0)
async def start() -> Any:
    await data_processor.data_manager.start_recording()
    asyncio.create_task(data_processor.data_manager.record_data())
    return {'message': 'Recording started.'}


@app.post("/stop_recording")
@version(1, 0)
async def stop() -> Any:
    await data_processor.data_manager.stop_recording()
    return {'message': 'Recording stopped.'}


# Assuming other imports and initializations are here


@app.get("/pointcloud")
@version(1, 0)
async def get_point_cloud():
    # Fetch the point cloud data from the sonar class
    point_cloud = ping_manager.get_point_cloud()

    if point_cloud is None or len(point_cloud) == 0:
        logger.warning("No point cloud data available.")
        return {"message": "No point cloud data available yet."}

    logger.debug(f"Point cloud shape: {point_cloud.shape}")

    # Assuming point_cloud is a NumPy array with shape (N, 2) for (y, x) coordinates
    y = point_cloud[:, 0]
    x = point_cloud[:, 1]

    # Create a plot
    plt.figure(figsize=(8, 8))
    plt.scatter(x, y, c='b', marker='.')
    plt.title('Sonar Point Cloud')
    plt.xlabel('X Coordinate (m)')
    plt.ylabel('Y Coordinate (m)')
    plt.axis('equal')
    plt.grid(True)

    # Save plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Serve the image as a streaming response
    return StreamingResponse(buf, media_type="image/png")


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


async def start_services():
    logger.info("Starting data processor.")
    asyncio.create_task(data_processor.receive_mavlink_data())
    asyncio.create_task(ping_manager.get_ping_data(
        transmit_duration=TRANSMIT_DURATION,
        sample_period=SAMPLE_PERIOD,
        transmit_frequency=TRANSMIT_FREQUENCY
    ))

    # Running the uvicorn server in the background
    config = Config(app=app, host="0.0.0.0", port=9050, log_config=None)
    server = Server(config)

    await server.serve()

if __name__ == "__main__":
    logger.debug("Starting SLAM.")
    if os.geteuid() != 0:
        logger.error(
            "You need root privileges to run this script.\nPlease try again, this time using **sudo**. Exiting."
        )
        sys.exit(1)

    asyncio.run(start_services())
