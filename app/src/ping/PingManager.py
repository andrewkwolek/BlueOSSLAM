from typing import Optional, Callable, Tuple, List
import asyncio
import os
import h5py
import numpy as np
from brping import Ping360
from brping import definitions
from loguru import logger

from .SonarFeatureExtraction import SonarFeatureExtraction
from settings import WATER_SOS, SonarConfig, CFARConfig


class PingManager:
    """
    Manages the Ping360 sonar device, processing scans and feature extraction.

    Attributes:
        feature_extractor: Processes sonar data to extract features
        resolution: The range resolution calculated from settings
        current_scan: The most recent complete scan data
        current_angles: The angles corresponding to the current scan
        costmap: The extracted feature costmap from the sonar data
        start_index: The starting index for valid range data
    """

    def __init__(self, device: Optional[str], baudrate: int, udp: str, live: bool = True):
        """
        Initialize the PingManager.

        Args:
            device: Serial device path for the Ping360
            baudrate: Baud rate for serial connection
            udp: UDP connection string in format "host:port"
            live: Whether to use a live Ping360 device or recorded data
        """
        self.current_scan = None
        self.current_angles = None
        self.start_index = 0

        # Calculate resolution based on acoustic properties and sample period
        self.resolution = (WATER_SOS * SonarConfig.SAMPLE_PERIOD * 25e-9) / 2

        # Initialize for live or replay mode
        if live:
            self._init_live_device(device, baudrate, udp)
        else:
            self._init_replay_mode()

        # Initialize feature extractor
        self.feature_extractor = SonarFeatureExtraction(
            Ntc=CFARConfig.Ntc, Ngc=CFARConfig.Ngc, Pfa=CFARConfig.Pfa, alg="GOCA")

        # Initialize other instance variables
        self.costmap = None
        self.X = None
        self.Y = None

        # Callback function for when current_scan is updated
        self._on_scan_updated_callback: Optional[Callable[[
            np.ndarray], None]] = None

    def _init_live_device(self, device: Optional[str], baudrate: int, udp: str):
        """Initialize the PingManager for live device mode."""
        self.myPing360 = Ping360()
        self.device = device
        self.baudrate = baudrate
        self.udp = udp

        try:
            # Connect to the device
            if device is not None:
                self.myPing360.connect_serial(device, self.baudrate)
            elif udp is not None:
                host, port = udp.split(':')
                self.myPing360.connect_udp(host, int(port))

            # Initialize the device
            self.myPing360.initialize()
            logger.info("Ping360 initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Ping360: {e}")
            raise RuntimeError("Failed to initialize Ping360 device")

    def _init_replay_mode(self):
        """Initialize the PingManager for replay mode (using recorded data)."""
        # Create angle list in degrees (0-399 gradians converted to 0-359.1 degrees)
        self.angles = [angle * (180/200) for angle in range(400)]
        logger.info("Initialized in replay mode")

    async def shutdown(self):
        """Safely shut down the Ping360 device."""
        try:
            if hasattr(self, 'device') and self.device is not None:
                # Reconnect if needed before shutting down
                self.myPing360.connect_serial(self.device, self.baudrate)

                # Turn the motor off
                self.myPing360.control_motor_off()
                logger.info("Ping360 motor turned off")
        except Exception as e:
            logger.error(f"Error during Ping360 shutdown: {e}")
        logger.info("Ping360 shut down")

    def register_scan_update_callback(self, callback: Callable[[np.ndarray], None]):
        """
        Register a callback function to be called when current_scan is updated.

        Args:
            callback: Function to call with the scan data when updated
        """
        self._on_scan_updated_callback = callback
        logger.info("Sonar callback registered")

    async def scan(self, angle: int, transmit_duration: int, sample_period: int, transmit_frequency: int):
        """
        Send a scan command to the Ping360 at the specified angle.

        Args:
            angle: Scan angle in gradians (0-399, where 200 = 180 degrees)
            transmit_duration: Duration of the sonar ping in microseconds
            sample_period: Time between samples in 25ns increments
            transmit_frequency: Frequency of the transmitted pulse in Hz
        """
        self.myPing360.control_transducer(
            mode=1,
            gain_setting=0,
            angle=angle,
            transmit_duration=transmit_duration,
            sample_period=sample_period,
            transmit_frequency=transmit_frequency,
            number_of_samples=1200,
            transmit=1,
            reserved=0
        )

    async def get_ping_data(self) -> Tuple[Optional[float], Optional[np.ndarray]]:
        """
        Wait for and process a single ping data message.

        Returns:
            Tuple of (angle, data_array) or (None, None) if no message received
        """
        m = self.myPing360.wait_message([definitions.PING360_DEVICE_DATA])
        if m:
            # Process and extract the data
            data_dict = {
                "mode": m.mode,
                "gain_setting": m.gain_setting,
                # Convert from gradians to degrees
                "angle": m.angle * (180 / 200),
                "transmit_duration": m.transmit_duration,
                "sample_period": m.sample_period,
                "transmit_frequency": m.transmit_frequency,
                "number_of_samples": m.number_of_samples,
                "data": np.frombuffer(m.data, dtype=np.uint8),
            }

            return data_dict['angle'], np.array(data_dict['data'])

        return None, None

    async def read_recording(self, filename: str):
        """
        Read sonar data from an HDF5 file and process it.

        Args:
            filename: Path to the HDF5 file containing sonar data
        """
        logger.info(f"Reading sonar data from {filename}")

        if not os.path.exists(filename):
            logger.error(f"File {filename} does not exist")
            return None

        try:
            with h5py.File(filename, 'r') as file:
                # List all saved scans
                datasets = list(file.keys())
                logger.info(f"Found {len(datasets)} scans")

                while True:  # Loop through the datasets repeatedly
                    for dataset in datasets:
                        if datasets:
                            # Load and process data
                            self.current_scan, self.start_index = self.clean(
                                file[dataset][:])
                            self.current_angles = self.angles

                            logger.debug(
                                f"Processed scan: min={np.min(self.current_scan)}, max={np.max(self.current_scan)}")

                            # Extract features if needed
                            # self.costmap, self.X, self.Y = await self.feature_extractor.extract_features(
                            #     self.current_scan, self.angles, self.resolution)

                            # Trigger callback if registered
                            if self._on_scan_updated_callback:
                                self._on_scan_updated_callback(
                                    self.current_scan)

                        else:
                            logger.warning("No scans found in file")

                        # Wait before processing the next dataset
                        await asyncio.sleep(15)
        except Exception as e:
            logger.error(f"Error opening or reading file {filename}: {e}")

    def get_data(self) -> np.ndarray:
        """Get the current scan data."""
        return self.current_scan

    def get_costmap(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get the current costmap and coordinate grids."""
        return self.costmap, self.X, self.Y

    def get_current_angles(self) -> List[float]:
        """Get the angles corresponding to the current scan."""
        return self.current_angles

    def get_cfar_polar(self) -> np.ndarray:
        """Get the CFAR-processed polar data."""
        return self.feature_extractor.get_cfar()

    def get_start_index(self) -> int:
        """Get the starting index for valid range data."""
        return self.start_index

    def clean(self, data: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Set sonar data below operating range to zero.

        Args:
            data: Raw sonar data array

        Returns:
            Tuple of (cleaned_data, start_index)
        """
        # Find index corresponding to minimum operating range (0.75m)
        index = 0
        while index * self.resolution < 0.75:
            data[index] = 0
            index += 1

        return data[index:], index

    async def sonar_scanning(self, start: int = 0, end: int = 399, threshold: int = 80):
        """
        Continuously scan with the sonar between the specified angles.

        Args:
            start: Starting angle in gradians (0-399)
            end: Ending angle in gradians (0-399)
            threshold: Minimum amplitude threshold for data
        """
        data_mat = []
        angles = []
        self.start_index = 0

        logger.info(f"Starting continuous scanning from {start} to {end}")

        step = start
        while True:
            try:
                # Send scan command
                await self.scan(step, SonarConfig.TRANSMIT_DURATION, SonarConfig.SAMPLE_PERIOD, SonarConfig.TRANSMIT_FREQUENCY)

                # Get scan data
                angle, data = await self.get_ping_data()

                if data is None:
                    logger.warning(f"Ping360 message empty at step {step}")
                    step = (step + 1) % 400
                    continue

                # Process data
                cleaned_data, self.start_index = self.clean(data)

                # Apply amplitude threshold
                cleaned_data[cleaned_data < threshold] = 0

                # Store data for this angle
                data_mat.append(cleaned_data)
                angles.append(angle)

                # If completed a full scan, process the complete dataset
                if step == end:
                    # Reset to start angle for next scan
                    step = start

                    # Convert list of 1D arrays to a 2D array and transpose
                    self.current_scan = np.array(data_mat).T
                    self.current_angles = angles

                    # Call the callback if registered
                    if self._on_scan_updated_callback:
                        self._on_scan_updated_callback(self.current_scan)

                    # Clear data for next scan
                    data_mat = []
                    angles = []

                    logger.debug("Completed full scan cycle")
                else:
                    # Move to next angle
                    step = (step + 1) % 400

                # Small delay to avoid overwhelming the device
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error during scanning: {e}")
                await asyncio.sleep(1)  # Longer delay on error
