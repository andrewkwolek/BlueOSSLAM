import asyncio
import numpy as np
from brping import Ping360
from brping import definitions
from typing import List, Optional, Dict
from loguru import logger
from typedefs import SonarData
from dataclasses import dataclass
import time


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


class SonarPointCloud:
    def __init__(self, max_points: int = 100000, decay_time: float = 30.0):
        """
        Initialize the point cloud manager.

        Args:
            max_points: Maximum number of points to store
            decay_time: Time in seconds after which points are removed
        """
        self.max_points = max_points
        self.decay_time = decay_time
        self.points: List[SonarPoint] = []

        # Sonar constants
        self.MIN_RANGE = 0.75  # meters
        self.MAX_RANGE = 50.0  # meters

    async def process_ping_data(self, ping_data: Dict,
                                mounting_height: float = 0.0,
                                mounting_angle: float = 0.0):
        """
        Process new sonar data and add it to the point cloud.

        Args:
            ping_data: Dictionary containing Ping360 data message
            mounting_height: Height of the sonar above reference plane (e.g., seafloor)
            mounting_angle: Tilt angle of the sonar in degrees
        """
        data = Ping360Data.from_dict(ping_data)

        # Convert angle from gradians to radians
        # Note: gradians are 1/400 of a full circle, radians are 1/2π of a full circle
        angle_rad = (data.angle * 2 * np.pi) / 400
        mounting_angle_rad = np.radians(mounting_angle)

        # Calculate range for each sample
        # The sample_period (in 25ns increments) affects the range calculation
        # Speed of sound in water ≈ 1500 m/s
        # Range = (speed_of_sound * sample_period * 25e-9 * sample_number) / 2
        # The division by 2 is because the sound has to travel there and back

        speed_of_sound = 1500  # m/s
        sample_time = data.sample_period * 25e-9  # convert to seconds
        max_range = (speed_of_sound * sample_time * data.number_of_samples) / 2
        ranges = np.linspace(self.MIN_RANGE, max_range, len(data.data))

        # Calculate positions for each point
        for range_val, intensity in zip(ranges, data.data):
            if intensity > 0 and self.MIN_RANGE <= range_val <= self.MAX_RANGE:
                # Calculate base x,y position
                x = range_val * np.cos(angle_rad)
                y = range_val * np.sin(angle_rad)

                # Apply mounting angle to adjust z
                z = mounting_height + range_val * np.sin(mounting_angle_rad)

                # Create new point
                point = SonarPoint(
                    x=x,
                    y=y,
                    z=z,
                    intensity=float(intensity),
                    timestamp=time.time()
                )

                self.points.append(point)

        # Maintain maximum size and remove old points
        self._cleanup()

    def _cleanup(self):
        """Remove old points and maintain maximum size."""
        current_time = time.time()

        # Remove points older than decay_time
        self.points = [p for p in self.points
                       if (current_time - p.timestamp) < self.decay_time]

        # If still too many points, remove oldest ones
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]

    def get_xyz_array(self) -> np.ndarray:
        """Return points as Nx3 numpy array for visualization."""
        if not self.points:
            return np.zeros((0, 3))
        return np.array([[p.x, p.y, p.z] for p in self.points])

    def get_intensities(self) -> np.ndarray:
        """Return intensity values as numpy array."""
        if not self.points:
            return np.zeros(0)
        return np.array([p.intensity for p in self.points])

    def clear(self):
        """Clear all points from the cloud."""
        self.points = []


class PingManager:
    def __init__(self, device, baudrate, udp):
        self.myPing360 = Ping360()
        self.point_cloud = SonarPointCloud()
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

        self.current_data = None

    async def get_ping_data(self):
        # Print the scanning head angle
        step = 0
        while True:
            self.myPing360.control_transducer(
                mode=1,
                gain_setting=0,
                angle=step,
                transmit_duration=80,
                sample_period=80,
                transmit_frequency=750,
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
                    "angle": m.angle,
                    "transmit_duration": m.transmit_duration,
                    "sample_period": m.sample_period,
                    "transmit_frequency": m.transmit_frequency,
                    "number_of_samples": m.number_of_samples,
                    "data": m.data,
                })
                logger.info(f"Angle: {self.data['angle']}")
                await self.point_cloud.process_ping_data(
                    ping_data=self.data,
                    mounting_height=0.0,  # Adjust based on your mounting
                    mounting_angle=0.0    # Adjust based on your mounting
                )
                logger.info(
                    f"Point cloud size: {len(self.point_cloud.get_xyz_array())}")
            step = (step + 1) % 400
            await asyncio.sleep(0.1)

    async def shutdown(self):
        if self.device is not None:
            self.myPing360.connect_serial(self.device, self.baudrate)

        # turn the motor off
        self.myPing360.control_motor_off()

        logger.info("Ping360 shutting down")

    @property
    def get_data(self):
        return self.data
