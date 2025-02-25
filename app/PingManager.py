from typing import List, Dict, Optional
import asyncio
import numpy as np
import matplotlib.pyplot as plt
from brping import Ping360
from brping import definitions
from loguru import logger
from dataclasses import dataclass
from SonarFeatureExtraction import SonarFeatureExtraction
import io


@dataclass
class SonarPoint:
    x: float
    y: float
    z: float
    intensity: float
    timestamp: float


@dataclass
class Ping360Data:
    mode: int
    gain_setting: int
    angle: int  # in gradians
    transmit_duration: int  # microseconds
    sample_period: int  # 25ns increments
    transmit_frequency: int  # kHz
    number_of_samples: int
    data: List[int]  # strength values

    @classmethod
    def from_dict(cls, data: Dict) -> 'Ping360Data':
        return cls(
            mode=data['mode'],
            gain_setting=data['gain_setting'],
            angle=data['angle'],
            transmit_duration=data['transmit_duration'],
            sample_period=data['sample_period'],
            transmit_frequency=data['transmit_frequency'],
            number_of_samples=data['number_of_samples'],
            data=data['data']
        )


class PingManager:
    def __init__(self, device, baudrate, udp):
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

        self.current_scan = None
        self.data_mat = []
        self.angles = []

        self.feature_extractor = SonarFeatureExtraction()
        self.features = None

    async def get_ping_data(self, transmit_duration, sample_period, transmit_frequency):
        # Print the scanning head angle
        step = 372
        while True:
            self.myPing360.control_transducer(
                mode=1,
                gain_setting=0,
                angle=step,
                transmit_duration=transmit_duration,
                sample_period=sample_period,
                transmit_frequency=transmit_frequency,
                number_of_samples=1024,
                transmit=1,
                reserved=0
            )
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
                logger.info(f"Angle: {self.data['angle']}")
                self.angles.append(self.data['angle'])
                self.data_mat.append(np.array(self.data['data']))

            if step == 27:
                step = 372
                self.current_scan = np.array(self.data_mat).T
                logger.debug(f"Angles: {len(self.angles)}")
                logger.debug(f"Num ranges: {len(self.current_scan)}")
                self.features = await self.feature_extractor.extract_features(self.current_scan, self.angles, 1481*0.000002/2)
                self.data_mat = []
                self.angles = []
            else:
                step = (step + 1) % 400
            await asyncio.sleep(0.1)

    async def shutdown(self):
        if self.device is not None:
            self.myPing360.connect_serial(self.device, self.baudrate)

        # turn the motor off
        self.myPing360.control_motor_off()

        logger.info("Ping360 shutting down")

    def get_data(self):
        return self.current_scan

    def get_point_cloud(self):
        return self.features
