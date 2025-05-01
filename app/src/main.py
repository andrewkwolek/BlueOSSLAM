#!/usr/bin/env python3
"""
SLAM main application for BlueROV.

This module serves as the entry point for the SLAM application,
initializing the web service and all necessary components.
"""
import asyncio
import io
import os
import sys
from typing import Dict, Any, Optional, Tuple

import numpy as np
from loguru import logger
from matplotlib import pyplot as plt
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi_versioning import VersionedFastAPI, version
from pydantic import BaseModel, Field, validator

from Processor import Processor
from ping.PingManager import PingManager
from ping.ScanRecorder import SonarRecorder
from settings import (
    DATA_FILEPATH,
    SONAR_FILEPATH,
    SONAR_FILE,
    UDP_PORT,
    LIVE_SONAR,
    WATER_SOS,
    CFARConfig,
    SonarConfig
)


class CFARParams(BaseModel):
    """
    Parameters for CFAR (Constant False Alarm Rate) algorithm.

    Attributes:
        ntc: Number of training cells (must be even)
        ngc: Number of guard cells (must be even)
        pfa: Probability of false alarm (0-1)
        threshold: Amplitude threshold for detection (0-255)
    """
    ntc: int = Field(..., ge=2,
                     description="Number of training cells (must be even)")
    ngc: int = Field(..., ge=2,
                     description="Number of guard cells (must be even)")
    pfa: float = Field(..., gt=0, lt=1,
                       description="Probability of false alarm (0-1)")
    threshold: int = Field(..., ge=0, le=255, description="Threshold (0-255)")

    @validator('ntc', 'ngc')
    def must_be_even(cls, v, values, **kwargs):
        """Validate that ntc and ngc are even numbers."""
        if v % 2 != 0:
            field_name = kwargs.get('field').name
            raise ValueError(f"{field_name} must be an even number")
        return v


# Global variables for shared state
SERVICE_NAME = "slam"
data_processor = None
ping_manager = None
scan_recorder = None

# Initialize FastAPI application
app = FastAPI(
    title="SLAM",
    description="SLAM service for BlueROV.",
    version="1.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.post("/update_cfar_params")
@version(1, 0)
async def update_cfar_params(params: CFARParams) -> Dict[str, Any]:
    """
    Update the CFAR parameters used for sonar feature extraction.

    Args:
        params: New CFAR parameters

    Returns:
        Status message

    Raises:
        HTTPException: If parameter update fails
    """
    try:
        # Check if ping_manager and feature_extractor exist
        if ping_manager is None or not hasattr(ping_manager, 'feature_extractor'):
            raise HTTPException(
                status_code=503,
                detail="Sonar system not initialized"
            )

        # Update the settings globally
        global CFARConfig
        CFARConfig.Ntc = params.ntc
        CFARConfig.Ngc = params.ngc
        CFARConfig.Pfa = params.pfa
        CFARConfig.THRESHOLD = params.threshold

        # Update the feature extractor parameters
        result = await ping_manager.feature_extractor.update_cfar_parameters(
            Ntc=params.ntc,
            Ngc=params.ngc,
            Pfa=params.pfa,
            threshold=params.threshold
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to update CFAR parameters"
            )

        logger.info(
            f"CFAR parameters updated: Ntc={params.ntc}, Ngc={params.ngc}, "
            f"Pfa={params.pfa}, threshold={params.threshold}"
        )

        return {
            "status": "success",
            "message": "CFAR parameters updated"
        }

    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    except Exception as e:
        logger.error(f"Error updating CFAR parameters: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating parameters: {str(e)}"
        )


@app.post("/record_ping")
@version(1, 0)
async def toggle_scan_recording() -> Dict[str, Any]:
    """
    Toggle sonar scan recording.

    Returns:
        Status message

    Raises:
        HTTPException: If recording toggle fails
    """
    try:
        if scan_recorder is None:
            raise HTTPException(
                status_code=503,
                detail="Sonar recorder not initialized"
            )

        if scan_recorder.file is None:
            scan_recorder.start_recording()
            message = "Recording started"
        else:
            scan_recorder.stop_recording()
            message = "Recording stopped"

        logger.info(message)
        return {"status": "success", "message": message}

    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    except Exception as e:
        logger.error(f"Error toggling scan recording: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error toggling recording: {str(e)}"
        )


@app.get("/costmap")
@version(1, 0)
async def get_costmap() -> StreamingResponse:
    """
    Get the current sonar point cloud as a visualization.

    Returns:
        PNG image showing the point cloud

    Raises:
        HTTPException: If point cloud generation fails
    """
    if ping_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Sonar system not initialized"
        )

    # Fetch the point cloud data
    costmap, x, y = ping_manager.get_costmap()

    if costmap is None or len(costmap) == 0:
        logger.warning("No point cloud data available")
        raise HTTPException(
            status_code=404,
            detail="No point cloud data available yet"
        )

    # Create visualization
    try:
        return await create_plot(
            x, y, costmap,
            title='Sonar Point Cloud',
            x_label='X Coordinate (m)',
            y_label='Y Coordinate (m)',
            plot_type='mesh'
        )
    except Exception as e:
        logger.error(f"Error creating costmap visualization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating visualization: {str(e)}"
        )


@app.get("/sonar_scan")
@version(1, 0)
async def get_scan_data() -> StreamingResponse:
    """
    Get the current sonar scan data as a visualization.

    Returns:
        PNG image showing the sonar scan

    Raises:
        HTTPException: If scan data visualization fails
    """
    if ping_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Sonar system not initialized"
        )

    scan_data = ping_manager.get_data()
    angles = ping_manager.get_current_angles()
    start_index = ping_manager.get_start_index()

    if angles is None or scan_data is None:
        logger.warning("Scan incomplete or no data available")
        raise HTTPException(
            status_code=404,
            detail="Scan incomplete or no data available"
        )

    try:
        return await create_range_azimuth_plot(
            scan_data, angles, start_index,
            title="Range-Azimuth Strength Spectrum"
        )
    except Exception as e:
        logger.error(f"Error creating sonar scan visualization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating visualization: {str(e)}"
        )


@app.get("/cfar_scan")
@version(1, 0)
async def get_cfar_data() -> StreamingResponse:
    """
    Get the current CFAR-processed sonar data as a visualization.

    Returns:
        PNG image showing the CFAR-processed scan

    Raises:
        HTTPException: If CFAR data visualization fails
    """
    if ping_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Sonar system not initialized"
        )

    scan_data = ping_manager.get_cfar_polar()
    angles = ping_manager.get_current_angles()
    start_index = ping_manager.get_start_index()

    if angles is None or scan_data is None:
        logger.warning("Scan incomplete or no CFAR data available")
        raise HTTPException(
            status_code=404,
            detail="Scan incomplete or no CFAR data available"
        )

    try:
        return await create_range_azimuth_plot(
            scan_data, angles, start_index,
            title="CFAR Strength Spectrum",
            colormap='viridis'
        )
    except Exception as e:
        logger.error(f"Error creating CFAR visualization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating visualization: {str(e)}"
        )


@app.get("/polar_scan")
@version(1, 0)
async def get_polar_scan_data() -> StreamingResponse:
    """
    Get the current sonar scan data as a polar visualization.

    Returns:
        PNG image showing the sonar scan in polar coordinates

    Raises:
        HTTPException: If polar visualization fails
    """
    if ping_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Sonar system not initialized"
        )

    scan_data = ping_manager.get_data()
    angles = ping_manager.get_current_angles()
    start_index = ping_manager.get_start_index()

    if angles is None or scan_data is None:
        logger.warning("Scan incomplete or no data available")
        raise HTTPException(
            status_code=404,
            detail="Scan incomplete or no data available"
        )

    try:
        return await create_polar_plot(
            scan_data, angles, start_index,
            title="Sonar Scan - Polar View"
        )
    except Exception as e:
        logger.error(f"Error creating polar visualization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating visualization: {str(e)}"
        )


async def create_range_azimuth_plot(
    scan_data: np.ndarray,
    angles: list,
    start_index: int,
    title: str = "Range-Azimuth Plot",
    colormap: str = 'viridis'
) -> StreamingResponse:
    """
    Create a range-azimuth plot from sonar data.

    Args:
        scan_data: Sonar data array
        angles: List of azimuth angles
        start_index: Starting index for range
        title: Plot title
        colormap: Matplotlib colormap name

    Returns:
        StreamingResponse with PNG image
    """
    azimuths = np.array(angles)

    # Range resolution calculation
    resolution = (WATER_SOS * SonarConfig.SAMPLE_PERIOD * 25e-9) / 2
    num_ranges = scan_data.shape[0]
    num_azimuths = scan_data.shape[1]

    # Define ranges based on resolution
    ranges = np.arange(
        start_index * resolution,
        (start_index + num_ranges) * resolution,
        resolution
    )

    # Create the plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    # Use extent to properly map the image to correct coordinates
    extent = [0, num_azimuths-1, ranges[0], ranges[-1]]
    im = ax.imshow(
        scan_data,
        cmap=colormap,
        aspect='auto',
        extent=extent,
        origin='lower',
        vmin=0,
        vmax=np.max(scan_data)
    )

    fig.suptitle(title, fontsize=14)
    ax.set_xlabel("Azimuth Angle (degrees)")
    ax.set_ylabel("Range (meters)")

    # Set evenly spaced range ticks
    num_range_ticks = 10
    range_tick_labels = np.linspace(
        ranges[0], ranges[-1], num_range_ticks).round(2)
    ax.set_yticks(range_tick_labels)

    # Set evenly spaced azimuth ticks
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
    plt.close(fig)

    # Serve the image as a streaming response
    return StreamingResponse(buf, media_type="image/png")


async def create_polar_plot(
    scan_data: np.ndarray,
    angles: list,
    start_index: int,
    title: str = "Polar Plot"
) -> StreamingResponse:
    """
    Create a polar plot from sonar data.

    Args:
        scan_data: Sonar data array
        angles: List of azimuth angles
        start_index: Starting index for range
        title: Plot title

    Returns:
        StreamingResponse with PNG image
    """
    azimuths = np.array(angles)

    # Range resolution calculation
    resolution = (WATER_SOS * SonarConfig.SAMPLE_PERIOD * 25e-9) / 2
    num_ranges = scan_data.shape[0]

    # Define ranges based on resolution
    ranges = np.arange(
        start_index * resolution,
        (start_index + num_ranges) * resolution,
        resolution
    )

    # Convert angles to radians for the polar plot
    theta = np.radians(azimuths)

    # Create a polar figure
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={
                           'projection': 'polar'})

    # Sort angles for proper plotting
    sorted_indices = np.argsort(theta)
    theta_sorted = theta[sorted_indices]
    Z = scan_data[:, sorted_indices]

    # Handle angle discontinuity (e.g., if scan crosses 0/360 degrees)
    if np.max(np.diff(theta_sorted)) > np.pi:
        # Find the discontinuity
        jump_idx = np.argmax(np.diff(theta_sorted))

        # Create arrays with repeated endpoints to close the gap
        theta_fixed = np.concatenate(
            [theta_sorted[jump_idx+1:], theta_sorted[:jump_idx+1] + 2*np.pi])
        Z_fixed = np.column_stack([Z[:, jump_idx+1:], Z[:, :jump_idx+1]])

        # Create a new meshgrid
        T_fixed, R_fixed = np.meshgrid(theta_fixed, ranges)

        # Plot with the fixed arrays
        cax = ax.pcolormesh(T_fixed, R_fixed, Z_fixed,
                            cmap='viridis', shading='auto')
    else:
        # Direct plotting if no discontinuity
        cax = ax.pcolormesh(
            theta_sorted, ranges, Z[:, sorted_indices],
            cmap='viridis', shading='auto'
        )

    # Add a colorbar
    cbar = fig.colorbar(cax, ax=ax, orientation='vertical', pad=0.1)
    cbar.set_label('Amplitude')

    # Set the direction of increasing angle to be counterclockwise
    ax.set_theta_direction(-1)

    # Set the "zero" angle to the top of the plot (forward direction)
    ax.set_theta_zero_location('N')

    # Set the radial limits to show only the valid range
    ax.set_rlim(0, num_ranges * resolution * 0.9)

    # Set grid and range labels at reasonable intervals
    r_ticks = np.linspace(0, ranges[-1], min(10, len(ranges)))
    ax.set_rticks(r_ticks)
    ax.set_yticklabels([f"{tick:.1f}m" for tick in r_ticks])

    # Customize angle labels
    ax.set_xticks(np.radians(np.arange(0, 360, 45)))  # Every 45 degrees

    # Set title
    fig.suptitle(title, fontsize=14)

    # Save plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    # Serve the image as a streaming response
    return StreamingResponse(buf, media_type="image/png")


async def create_plot(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    title: str = "Plot",
    x_label: str = "X",
    y_label: str = "Y",
    plot_type: str = 'mesh'
) -> StreamingResponse:
    """
    Create a generic 2D plot with provided data.

    Args:
        x: X-axis data
        y: Y-axis data
        z: Z-axis data (for color mapping)
        title: Plot title
        x_label: X-axis label
        y_label: Y-axis label
        plot_type: Type of plot ('mesh' or 'contour')

    Returns:
        StreamingResponse with PNG image
    """
    plt.figure(figsize=(8, 8))

    if plot_type == 'mesh':
        plt.pcolormesh(x, y, z, cmap='viridis')
    elif plot_type == 'contour':
        plt.contourf(x, y, z, cmap='viridis')
    else:
        plt.pcolormesh(x, y, z, cmap='viridis')

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.axis('equal')
    plt.grid(True)
    plt.colorbar(label='Value')

    # Save plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Serve the image as a streaming response
    return StreamingResponse(buf, media_type="image/png")


# Apply versioning to the FastAPI app
app = VersionedFastAPI(
    app,
    version="1.0.0",
    prefix_format="/v{major}.{minor}",
    enable_latest=True,
)

# Mount static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
async def root() -> HTMLResponse:
    """Root endpoint that serves the index.html file."""
    return HTMLResponse(content="index.html", status_code=200)


async def setup_services() -> Tuple[Processor, PingManager, SonarRecorder]:
    """
    Initialize all services required for the application.

    Returns:
        Tuple of (data_processor, ping_manager, scan_recorder)
    """
    # Create data processor
    logger.info("Initializing data processor")
    processor = Processor()

    # Create directories if they don't exist
    os.makedirs(DATA_FILEPATH, exist_ok=True)
    os.makedirs(SONAR_FILEPATH, exist_ok=True)

    # Create ping manager
    logger.info("Initializing ping manager")
    ping_mgr = PingManager(
        device=None,
        baudrate=115200,
        udp=UDP_PORT,
        live=LIVE_SONAR
    )

    # Create sonar recorder
    logger.info("Initializing sonar recorder")
    recorder = SonarRecorder()

    # Register sonar callback
    logger.info("Registering sonar callback")
    ping_mgr.register_scan_update_callback(recorder.save_scan)

    return processor, ping_mgr, recorder


async def start_services() -> None:
    """Initialize and start all services."""
    global data_processor, ping_manager, scan_recorder

    try:
        # Setup services
        data_processor, ping_manager, scan_recorder = await setup_services()

        # Start data processor
        logger.info("Starting data processor")
        # await data_processor.start()

        # Start ping manager
        if LIVE_SONAR:
            logger.info("Starting live sonar data collection")
            asyncio.create_task(ping_manager.get_ping_data(
                transmit_duration=SonarConfig.TRANSMIT_DURATION,
                sample_period=SonarConfig.SAMPLE_PERIOD,
                transmit_frequency=SonarConfig.TRANSMIT_FREQUENCY
            ))
        else:
            logger.info("Starting sonar data replay")
            asyncio.create_task(ping_manager.read_recording(
                f"/app/sonar_data/{SONAR_FILE}"
            ))

        # Running the uvicorn server
        import uvicorn
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=9050,
            log_config=None
        )
        server = uvicorn.Server(config)

        logger.info("Starting web server")
        await server.serve()

    except Exception as e:
        logger.error(f"Error starting services: {e}")
        # Attempt to clean up
        if data_processor:
            await data_processor.stop()
        if ping_manager and hasattr(ping_manager, 'shutdown'):
            await ping_manager.shutdown()
        sys.exit(1)


async def cleanup() -> None:
    """Clean up resources on shutdown."""
    if data_processor:
        await data_processor.stop()
    if ping_manager and hasattr(ping_manager, 'shutdown'):
        await ping_manager.shutdown()


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME}")

    # Check if running as root
    if os.geteuid() != 0:
        logger.error(
            "You need root privileges to run this script.\n"
            "Please try again, this time using **sudo**. Exiting."
        )
        sys.exit(1)

    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Ensure we clean up resources
        asyncio.run(cleanup())
