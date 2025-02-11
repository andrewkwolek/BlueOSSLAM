#! /usr/bin/env python3
import asyncio
import os
import sys
from loguru import logger
from typing import Any

from DataManager import DataManager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi_versioning import VersionedFastAPI, version
from loguru import logger
from MavlinkUDP import MavlinkUDPProtocol
from PingManager import PingManager
from uvicorn import Config, Server

from settings import PING_DEVICE, UDP_PORT, DOCKER_HOST

SERVICE_NAME = "slam"

app = FastAPI(
    title="SLAM",
    description="SLAM service.",
    debug=True,
)

logger.info(f"Starting {SERVICE_NAME}")
data_manager = DataManager()
ping_manager = PingManager(baudrate=115200, udp=UDP_PORT)


@app.get("/gps")
@version(1, 0)
async def get_gps_data() -> Any:
    logger.debug("Fetching GPS data.")
    return await data_manager.get_gps_data()


@app.get("/imu")
@version(1, 0)
async def get_gps_data() -> Any:
    logger.debug("Fetching IMU data.")
    return await data_manager.get_imu_data()


@app.get("/attitude")
@version(1, 0)
async def get_gps_data() -> Any:
    logger.debug("Fetching attitude data.")
    return await data_manager.get_attitude_data()


@app.get("/ping")
@version(1, 0)
async def get_ping_data() -> Any:
    logger.debug("Fetching ping data.")
    return await ping_manager.get_ping_data()


@app.post("/start_recording")
@version(1, 0)
async def start() -> Any:
    await data_manager.start_recording()
    asyncio.create_task(data_manager.record_data())
    return {'message': 'Recording started.'}


@app.post("/stop_recording")
@version(1, 0)
async def stop() -> Any:
    await data_manager.stop_recording()
    return {'message': 'Recording stopped.'}


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


async def listen_udp():
    # Listening for UDP packets on this address and port
    listen_address = (DOCKER_HOST, 14550)

    loop = asyncio.get_running_loop()

    # Set up the UDP endpoint to listen for incoming datagrams
    listen = await loop.create_datagram_endpoint(
        # Use lambda to pass data_manager to protocol
        lambda: MavlinkUDPProtocol(data_manager),
        # Listen on all available network interfaces (0.0.0.0)
        local_addr=listen_address
    )

    logger.info(f"Listening for UDP packets on {listen_address}")

    # The event loop will now handle the datagrams asynchronously
    # listen_udp will continue running and processing incoming data.
    await asyncio.Future()
    logger.info(f"Exiting")


async def start_services():
    asyncio.create_task(listen_udp())

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
