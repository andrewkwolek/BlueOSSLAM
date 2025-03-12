#! /usr/bin/env python3
from matplotlib import pyplot as plt
import io
from fastapi.responses import StreamingResponse
import asyncio
import os
import h5py
import sys
import numpy as np
from loguru import logger
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi_versioning import VersionedFastAPI, version
from Processor import Processor
from pydantic import BaseModel
from ping.PingManager import PingManager
from ping.ScanRecorder import SonarRecorder
from uvicorn import Config, Server

from settings import *


class CFARParams(BaseModel):
    ntc: int
    ngc: int
    pfa: float
    threshold: int


SERVICE_NAME = "slam"

app = FastAPI(
    title="SLAM",
    description="SLAM service.",
    debug=True,
)

logger.info(f"Starting {SERVICE_NAME}")
data_processor = Processor()
ping_manager = PingManager(
    device=None, baudrate=115200, udp=UDP_PORT, live=LIVE_SONAR)
scan_recorder = SonarRecorder()

logger.info("Register sonar callback")
ping_manager.register_scan_update_callback(scan_recorder.save_scan)


@app.post("/update_cfar_params")
@version(1, 0)
async def update_cfar_params(params: CFARParams):
    # Validate the parameters
    if params.ntc % 2 != 0:
        return {"detail": "Ntc must be an even number"}

    if params.ngc % 2 != 0:
        return {"detail": "Ngc must be an even number"}

    if params.pfa <= 0 or params.pfa > 1:
        return {"detail": "Pfa must be between 0 and 1"}

    if params.threshold <= 0 or params.threshold > 255:
        return {"detail": "Threshold must be between 0 and 255"}

    # Update the CFAR parameters
    try:
        # Update the settings module values (if needed for future initializations)
        global Ntc, Ngc, Pfa, threshold
        Ntc = params.ntc
        Ngc = params.ngc
        Pfa = params.pfa
        threshold = params.threshold

        # Use the new update method instead of reinitializing
        result = await ping_manager.feature_extractor.update_cfar_parameters(
            Ntc=params.ntc, Ngc=params.ngc, Pfa=params.pfa, threshold=params.threshold)

        if result:
            logger.info(
                f"CFAR parameters updated: Ntc={params.ntc}, Ngc={params.ngc}, Pfa={params.pfa}, threshold={params.threshold}")
            return {"status": "success", "message": "CFAR parameters updated"}
        else:
            return {"detail": "Failed to update CFAR parameters"}
    except Exception as e:
        logger.error(f"Error updating CFAR parameters: {str(e)}")
        return {"detail": f"Error updating parameters: {str(e)}"}


@app.post("/record_ping")
@version(1, 0)
async def toggle_scan_recording():
    if scan_recorder.file is None:
        scan_recorder.start_recording()
    else:
        scan_recorder.stop_recording()

    return {"status": "success"}


@app.get("/costmap")
@version(1, 0)
async def get_costmap():
    # Fetch the point cloud data from the sonar class
    costmap, x, y = ping_manager.get_costmap()

    if costmap is None or len(costmap) == 0:
        logger.warning("No point cloud data available.")
        return {"message": "No point cloud data available yet."}

    # Create a plot
    plt.figure(figsize=(8, 8))
    plt.pcolormesh(x, y, costmap)
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


@app.get("/sonar_scan")
@version(1, 0)
async def get_scan_data():
    scan_data = ping_manager.get_data()
    angles = ping_manager.get_current_angles()

    if angles is None:
        logger.warning("Scan incomplete!")
        return

    azimuths = np.array(angles)

    # Range resolution calculation
    resolution = (WATER_SOS * SAMPLE_PERIOD * 25e-9) / 2
    num_ranges = scan_data.shape[0]
    num_azimuths = scan_data.shape[1]

    # Define ranges based on resolution
    ranges = np.arange(0, num_ranges * resolution, resolution)

    # Power spectrum (apply log transform for better visualization)
    range_azimuth_psd = scan_data

    # Plot the power spectrum
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    # Use extent to properly map the image to correct coordinates
    extent = [0, num_azimuths-1, ranges[0], ranges[-1]]
    im = ax.imshow(range_azimuth_psd, cmap='viridis', aspect='auto',
                   extent=extent, origin='lower', vmin=0, vmax=np.max(range_azimuth_psd))

    fig.suptitle("Range-Azimuth Strength Spectrum", fontsize=14)
    ax.set_xlabel("Azimuth Angle (degrees)")
    ax.set_ylabel("Range (meters)")

    # Set evenly spaced range ticks
    num_range_ticks = 10
    range_tick_labels = np.linspace(
        ranges[0], ranges[-1], num_range_ticks).round(2)
    ax.set_yticks(range_tick_labels)

    # Set evenly spaced azimuth ticks that correspond to actual column indices
    num_azimuth_ticks = min(9, num_azimuths)
    azimuth_indices = np.linspace(
        0, num_azimuths-1, num_azimuth_ticks).astype(int)
    azimuth_tick_labels = np.round(azimuths[azimuth_indices], 1)
    ax.set_xticks(azimuth_indices)
    ax.set_xticklabels(azimuth_tick_labels)

    ax.grid(True, linestyle='--', alpha=0.7)

    # Save plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    # Serve the image as a streaming response
    return StreamingResponse(buf, media_type="image/png")


@app.get("/cfar_scan")
@version(1, 0)
async def get_cfar_data():
    scan_data = ping_manager.get_cfar_polar()
    angles = ping_manager.get_current_angles()

    if angles is None:
        logger.warning("Scan incomplete!")
        return

    azimuths = np.array(angles)

    # Range resolution calculation
    resolution = (WATER_SOS * SAMPLE_PERIOD * 25e-9) / 2
    num_ranges = scan_data.shape[0]
    num_azimuths = scan_data.shape[1]  # Make sure to get the correct dimension

    # Define ranges based on resolution
    ranges = np.arange(0, num_ranges * resolution, resolution)

    # Power spectrum (apply log transform for better visualization)
    # range_azimuth_psd = np.log10(scan_data.astype(np.float32) + 1.0)
    range_azimuth_psd = scan_data

    # Plot the power spectrum
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    # Use extent to properly map the image to correct coordinates
    extent = [0, num_azimuths-1, ranges[0], ranges[-1]]
    im = ax.imshow(range_azimuth_psd, cmap='viridis', aspect='auto',
                   extent=extent, origin='lower', vmin=0, vmax=np.max(range_azimuth_psd))

    fig.suptitle("CFAR Strength Spectrum", fontsize=14)
    ax.set_xlabel("Azimuth Angle (degrees)")
    ax.set_ylabel("Range (meters)")

    # Set evenly spaced range ticks
    num_range_ticks = 10
    range_tick_labels = np.linspace(
        ranges[0], ranges[-1], num_range_ticks).round(2)
    ax.set_yticks(range_tick_labels)

    # Set evenly spaced azimuth ticks that correspond to actual column indices
    num_azimuth_ticks = min(9, num_azimuths)
    azimuth_indices = np.linspace(
        0, num_azimuths-1, num_azimuth_ticks).astype(int)
    azimuth_tick_labels = np.round(azimuths[azimuth_indices], 1)
    ax.set_xticks(azimuth_indices)
    ax.set_xticklabels(azimuth_tick_labels)

    ax.grid(True, linestyle='--', alpha=0.7)

    # Save plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
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
    # asyncio.create_task(data_processor.receive_mavlink_data())
    if LIVE_SONAR:
        asyncio.create_task(ping_manager.get_ping_data(
            transmit_duration=TRANSMIT_DURATION,
            sample_period=SAMPLE_PERIOD,
            transmit_frequency=TRANSMIT_FREQUENCY
        ))
    else:
        asyncio.create_task(ping_manager.read_recording(
            "/app/sonar_data/sonar_better.h5"))

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
