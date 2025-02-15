#! /usr/bin/env python3
import asyncio
import cv2
import os
import sys
import numpy as np
from loguru import logger
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi_versioning import VersionedFastAPI, version
from loguru import logger
from Processor import Processor
from uvicorn import Config, Server

from video_odometry import MonoVideoOdometery
from video_capture import Video

from settings import PING_DEVICE, UDP_PORT, DOCKER_HOST

SERVICE_NAME = "slam"

app = FastAPI(
    title="SLAM",
    description="SLAM service.",
    debug=True,
)

logger.info(f"Starting {SERVICE_NAME}")
data_processor = Processor(baudrate=115200, udp=UDP_PORT)


@app.get("/gps")
@version(1, 0)
async def get_gps_data() -> Any:
    logger.debug("Fetching GPS data.")
    return await data_processor.data_manager.get_gps_data()


@app.get("/imu")
@version(1, 0)
async def get_gps_data() -> Any:
    logger.debug("Fetching IMU data.")
    return await data_processor.data_manager.get_imu_data()


@app.get("/attitude")
@version(1, 0)
async def get_gps_data() -> Any:
    logger.debug("Fetching attitude data.")
    return await data_processor.data_manager.get_attitude_data()


@app.get("/ping")
@version(1, 0)
async def get_ping_data() -> Any:
    logger.debug("Fetching ping data.")
    return await data_processor.ping_manager.get_ping_data()


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


async def v0():
    focal = 1188.0
    pp = (960, 540)
    R_total = np.zeros((3, 3))
    t_total = np.empty(shape=(3, 1))

    # Parameters for lucas kanade optical flow
    lk_params = dict(winSize=(21, 21),
                     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))

    vo = MonoVideoOdometery(focal, pp, lk_params)
    traj = np.zeros(shape=(600, 800, 3))

    flag = False

    video = Video()

    print('Initialising stream...')
    waited = 0
    while not video.frame_available():
        waited += 1
        print('\r  Frame not available (x{})'.format(waited), end='')
        cv2.waitKey(30)
    print('\nSuccess!\nStarting streaming - press "q" to quit.')

    while True:
        if video.frame_available():
            frame = await video.frame()

            await vo.process_frame(frame)

            mono_coord = await vo.get_mono_coordinates()

            print("x: {}, y: {}, z: {}".format(
                *[str(pt) for pt in mono_coord]))

        await asyncio.sleep(0)


async def start_services():
    logger.info("Starting visual odometry.")
    asyncio.create_task(v0())

    logger.info("Starting data processor.")
    asyncio.create_task(data_processor.receive_mavlink_data())

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
