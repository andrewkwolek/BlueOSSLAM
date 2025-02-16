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
data_processor = Processor(device=None, baudrate=115200, udp=UDP_PORT)


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
    lk_params = dict(winSize=(21, 21),
                     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))

    # Initialize Visual Odometry
    vo = MonoVideoOdometery(focal, pp, lk_params)

    # Initialize trajectory visualization with white background
    traj = np.ones((600, 800, 3), dtype=np.uint8) * 255

    # Scale factor for visualization
    scale_factor = 5.0

    video = Video()
    logger.info('Initializing stream...')
    while not video.frame_available():
        pass
    logger.info('Stream initialized!')

    save_interval = 100  # Save trajectory image every N frames
    frame_count = 0

    while True:
        if video.frame_available():
            frame = video.frame()

            # Process frame
            await vo.process_frame(frame)
            current_pos = await vo.get_mono_coordinates()

            # Scale the coordinates and negate Y (right is positive)
            draw_y = int(round(-current_pos[1] * scale_factor))
            draw_x = int(round(current_pos[0] * scale_factor))

            # Draw black trail
            cv2.circle(traj, (draw_y + 400, draw_x + 300), 1, (0, 0, 0), 2)

            # Draw coordinate axes
            origin = (400, 300)
            axes_length = 50
            axes_colors = [(0, 0, 255), (0, 255, 0)]

            # X-axis vertical (forward/back) in red
            cv2.arrowedLine(traj, origin, (origin[0], origin[1] - axes_length),
                            axes_colors[0], 2)
            # Y-axis horizontal (right is positive) in green
            cv2.arrowedLine(traj, origin, (origin[0] + axes_length, origin[1]),
                            axes_colors[1], 2)

            # Add labels
            cv2.putText(traj, 'X (forward)', (origin[0] - 20, origin[1] - axes_length - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            cv2.putText(traj, 'Y (right)', (origin[0] + axes_length + 10, origin[1] + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

            # Show current position values (unscaled)
            pos_text = f"X: {current_pos[0]:.2f} Y: {-current_pos[1]:.2f}"
            cv2.putText(traj, pos_text, (30, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 0), 2)

            # Print position to console
            logger.info(
                f"Position - X: {current_pos[0]:.2f} Y: {-current_pos[1]:.2f}")

            # Save trajectory image periodically
            frame_count += 1
            if frame_count % save_interval == 0:
                cv2.imwrite(f"trajectory_{frame_count}.png", traj)


async def start_services():
    logger.info("Starting visual odometry.")
    asyncio.create_task(v0())

    logger.info("Starting data processor.")
    asyncio.create_task(data_processor.receive_mavlink_data())
    asyncio.create_task(data_processor.ping_manager.get_ping_data())

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
