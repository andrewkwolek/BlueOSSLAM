from typing import Optional, Callable
import asyncio
import os
import h5py
import numpy as np
from brping import Ping360
from brping import definitions
from loguru import logger
from .SonarFeatureExtraction import SonarFeatureExtraction

from settings import WATER_SOS, TRANSMIT_DURATION, TRANSMIT_FREQUENCY, SAMPLE_PERIOD, Ntc, Ngc, Pfa


class PingManager:
    def __init__(self, device, baudrate, udp, live=True):
        if live:
            self.myPing360 = Ping360()
            self.device = None
            self.baudrate = baudrate
            self.udp = udp
            if device is not None:
                self.myPing360.connect_serial(self.device, self.baudrate)
            elif self.udp is not None:
                (host, port) = udp.split(':')
                self.myPing360.connect_udp(host, int(port))

            try:
                self.myPing360.initialize()
            except:
                logger.error("Failed to initialize Ping!")
                exit(1)
        else:
            self.angles = [334.8, 335.7, 336.6, 337.5, 338.4, 339.3, 340.2, 341.1, 342,  342.9, 343.8, 344.7,
                           345.6, 346.5, 347.4, 348.3, 349.2, 350.1, 351,  351.9, 352.8, 353.7, 354.6, 355.5,
                           356.4, 357.3, 358.2, 359.1,   0,    0.9,   1.8,   2.7,   3.6,   4.5,   5.4,   6.3,
                           7.2,   8.1,   9,    9.9,  10.8,  11.7,  12.6,  13.5,  14.4,  15.3,  16.2,  17.1,
                           18,   18.9,  19.8,  20.7,  21.6,  22.5,  23.4,  24.3]

        self.feature_extractor = SonarFeatureExtraction(
            Ntc=Ntc, Ngc=Ngc, Pfa=Pfa, alg="GOCA")
        self.features = None

        self.costmap = None
        self.X = None
        self.Y = None

        self.resolution = (WATER_SOS*SAMPLE_PERIOD*25e-9)/2

        # Callback function for when current_scan is updated
        self._on_scan_updated_callback: Optional[Callable[[
            np.ndarray], None]] = None

    async def shutdown(self):
        if self.device is not None:
            self.myPing360.connect_serial(self.device, self.baudrate)

        # turn the motor off
        self.myPing360.control_motor_off()

        logger.info("Ping360 shutting down")

    def register_scan_update_callback(self, callback: Callable[[np.ndarray], None]):
        """Register a callback function to be called when current_scan is updated."""
        self._on_scan_updated_callback = callback
        logger.info("Sonar callback registered.")

    async def scan(self, angle, transmit_duration, sample_period, transmit_frequency):
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

    async def get_ping_data(self):
        # Print the scanning head angle

        m = self.myPing360.wait_message(
            [definitions.PING360_DEVICE_DATA])
        if m:
            self.data = ({
                "mode": m.mode,
                "gain_setting": m.gain_setting,
                "angle": m.angle * (180 / 200),
                "transmit_duration": m.transmit_duration,
                "sample_period": m.sample_period,
                "transmit_frequency": m.transmit_frequency,
                "number_of_samples": m.number_of_samples,
                "data": np.frombuffer(m.data, dtype=np.uint8),
            })

            return self.data['angle'], np.array(self.data['data'])

        return None, None

    async def read_recording(self, filename):
        logger.info("Reading sonar data.")
        if os.path.exists(filename):
            with h5py.File(filename, 'r') as file:
                # List all saved scans
                datasets = list(file.keys())
                logger.info(f"Found scans: {datasets}")

                for dataset in datasets:
                    if datasets:
                        self.current_scan, self.start_index = self.clean(
                            file[dataset][:])
                        logger.debug(
                            f"Max: {np.max(self.current_scan)}, Min: {np.min(self.current_scan)}")
                        self.current_angles = self.angles
                        self.costmap, self.X, self.Y = await self.feature_extractor.extract_features(self.current_scan, self.angles, self.resolution)
                    else:
                        logger.warning("No scans found in file.")
                    await asyncio.sleep(15)
        else:
            logger.error(f"File {filename} does not exist.")
            return None

    def get_data(self):
        return self.current_scan

    def get_costmap(self):
        return self.costmap, self.X, self.Y

    def get_current_angles(self):
        return self.current_angles

    def get_cfar_polar(self):
        return self.feature_extractor.get_cfar()

    def get_start_index(self):
        return self.start_index

    def clean(self, data):
        """Sonar data below operating range get set to zero."""
        index = 0
        while index*self.resolution < 0.75:
            data[index] = 0
            index += 1

        return data[index:], index

    async def sonar_scanning(self, start=0, end=399, threshold=80):
        self.current_scan = None
        self.current_angles = None
        data_mat = []
        angles = []
        range = []

        self.start_index = 0

        step = start
        while True:
            await self.scan(step, TRANSMIT_DURATION,
                            SAMPLE_PERIOD, TRANSMIT_FREQUENCY)
            data, angle = await self.get_ping_data()

            if data is None:
                logger.warning(f"Ping360 message empty at step {step}!")
                step = (step + 1) % 400
                continue

            # Remove data out of operating range and identify starting index
            cleaned_data, self.start_index = self.clean(data)

            # Apply a conservatively high amplitude threshold
            cleaned_data[cleaned_data < threshold] = 0

            data_mat.append(cleaned_data)
            angles.append(angle)

            if step == end:
                step = start
                self.current_scan = np.array(data_mat).T
                self.current_angles = angles

                if self._on_scan_updated_callback:
                    self._on_scan_updated_callback(self.current_scan)

                data_mat = []
                angles = []
            else:
                step = (step + 1) % 400

            asyncio.sleep(0.1)
