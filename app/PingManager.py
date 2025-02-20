from sklearn.cluster import DBSCAN
from typing import List, Dict, Optional
import asyncio
import numpy as np
from brping import Ping360
from brping import definitions
from typing import List, Optional, Dict
from loguru import logger
from dataclasses import dataclass
import time

from CFAR import CFAR
from SonarFeatureExtraction import SonarFeatureExtraction


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


# class EnhancedSonarPointCloud:
#     def __init__(self,
#                  max_points: int = 100000,
#                  decay_time: float = 30.0,
#                  min_range: float = 0.75,
#                  max_range: float = 50.0,
#                  horizontal_spread: float = 2.0,  # Ping360 horizontal beam spread
#                  vertical_spread: float = 50.0):  # Ping360 vertical beam spread
#         self.max_points = max_points
#         self.decay_time = decay_time
#         self.min_range = min_range
#         self.max_range = max_range
#         self.horizontal_spread = np.radians(horizontal_spread)
#         self.vertical_spread = np.radians(vertical_spread)
#         self.points: List[SonarPoint] = []

#     async def process_ping_data(self,
#                                 ping_data: Dict,
#                                 fss_position: np.ndarray,  # [x, y, z]
#                                 fss_rotation_matrix: np.ndarray,  # 3x3 rotation matrix
#                                 tilt_angle: float):  # in degrees
#         """
#         Process sonar data using the highlight extension method,
#         accounting for Ping360's asymmetric beam pattern.

#         Args:
#             ping_data: Dictionary containing Ping360 data
#             fss_position: Global position of the sonar [x, y, z]
#             fss_rotation_matrix: Rotation matrix from sonar to global coordinates
#             tilt_angle: Tilt angle of the sonar in degrees
#         """
#         # Convert angle from gradians to radians (Ping360 uses gradians)
#         azimuth = (ping_data['angle'] * 2 * np.pi) / 400

#         # Calculate range for each sample
#         speed_of_sound = 1500  # m/s
#         sample_time = ping_data['sample_period'] * 25e-9  # convert to seconds
#         max_range = (speed_of_sound * sample_time *
#                      ping_data['number_of_samples']) / 2
#         ranges = np.linspace(self.min_range, max_range, len(ping_data['data']))

#         # Using equation (1) from the paper with modified elevation angle calculation
#         tilt_rad = np.radians(tilt_angle)

#         # The vertical beam is much wider, so we can detect objects within the entire vertical spread
#         # This gives us multiple potential elevation angles for each return
#         # We'll sample points along the vertical spread to better represent the possible locations
#         num_vertical_samples = 5  # Number of points to sample along vertical spread
#         elevation_angles = np.linspace(
#             tilt_rad - self.vertical_spread/2,
#             tilt_rad + self.vertical_spread/2,
#             num_vertical_samples
#         )

#         for range_val, intensity in zip(ranges, ping_data['data']):
#             if intensity > 0 and self.min_range <= range_val <= self.max_range:
#                 # For each strong return, create multiple points along the vertical spread
#                 intensity_per_point = intensity / num_vertical_samples  # Distribute intensity

#                 for elevation_angle in elevation_angles:
#                     # Calculate horizontal uncertainty
#                     azimuth_with_spread = azimuth + np.random.uniform(
#                         -self.horizontal_spread/2,
#                         self.horizontal_spread/2
#                     )

#                     # Calculate local coordinates as per equation (1)
#                     local_coords = np.array([
#                         range_val *
#                         np.sqrt(1 - np.sin(azimuth_with_spread) **
#                                 2 - np.sin(elevation_angle)**2),
#                         range_val * np.sin(azimuth_with_spread),
#                         range_val * np.sin(elevation_angle)
#                     ])

#                     # Transform to global coordinates
#                     global_coords = fss_position + fss_rotation_matrix @ local_coords

#                     point = SonarPoint(
#                         x=float(global_coords[0]),
#                         y=float(global_coords[1]),
#                         z=float(global_coords[2]),
#                         intensity=float(intensity_per_point),
#                         timestamp=time.time()
#                     )

#                     self.points.append(point)

#         self._cleanup()
#         self._remove_noise()

#     def _remove_noise(self, eps: float = 0.5, min_samples: int = 5):
#         """
#         Remove noise using DBSCAN clustering from sklearn.
#         """
#         if not self.points:
#             return

#         # Convert points to numpy array for DBSCAN
#         points_array = self.get_xyz_array()

#         # Perform DBSCAN clustering
#         dbscan = DBSCAN(eps=eps, min_samples=min_samples)
#         labels = dbscan.fit_predict(points_array)

#         # Keep only points that belong to clusters (label != -1)
#         self.points = [point for point, label in zip(
#             self.points, labels) if label != -1]

#     def _cleanup(self):
#         """Remove old points and maintain maximum size."""
#         current_time = time.time()
#         self.points = [p for p in self.points
#                        if (current_time - p.timestamp) < self.decay_time]

#         if len(self.points) > self.max_points:
#             self.points = self.points[-self.max_points:]

#     def get_xyz_array(self) -> np.ndarray:
#         """Return points as Nx3 numpy array for visualization."""
#         if not self.points:
#             return np.zeros((0, 3))
#         return np.array([[p.x, p.y, p.z] for p in self.points])

#     def get_intensities(self) -> np.ndarray:
#         """Return intensity values as numpy array."""
#         if not self.points:
#             return np.zeros(0)
#         return np.array([p.intensity for p in self.points])


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

    async def get_ping_data(self):
        # Print the scanning head angle
        step = 372
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

            if step == 27:
                step = 372
                self.current_scan = np.array(self.data_mat).T
                self.features = await self.feature_extractor.extract_features(self.current_scan, self.angles, 1481*0.000002/2)
                self.data_mat = []
                self.angles = []
            else:
                self.angles.append(self.data['angle'])
                self.data_mat.append(np.array(self.data['data']))
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
        return self.current_scan
