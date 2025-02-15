import numpy as np
import math
from brping import Ping360
from typedefs import SonarData
from loguru import logger


class IncrementalSonarPointCloudManager:
    def __init__(self, max_range=50, min_range=0.75, alpha=2.0, calibration_factor=1.0):
        self.max_range = max_range
        self.min_range = min_range
        self.alpha = alpha
        self.calibration_factor = calibration_factor
        self.point_cloud = []
        self.current_angle = 0  # Track the current horizontal angle
        self.vertical_angle = 0  # Track the current vertical angle (optional)

    def strength_to_distance(self, strength, max_range=50, min_range=0.75, alpha=2.0, calibration_factor=1.0):
        """
        Convert sonar signal strength to distance using a modified model based on the sonar's specs.
        """
        if strength > 0:
            # Apply inverse power law to map strength to distance
            distance = calibration_factor / (strength ** alpha)

            # Ensure the distance is within the defined range
            distance = max(min_range, min(distance, max_range))

            # Calculate range resolution based on current distance
            if distance >= 50:
                resolution = 0.041  # 4.1 cm at 50 meters
            elif distance <= 2:
                resolution = 0.0016  # 1.6 mm at 2 meters
            else:
                # Linear interpolation between 2m and 50m
                resolution = 0.041 * (distance / 50)

            # Adjust distance with resolution (error)
            distance += resolution
            return distance
        else:
            return max_range  # If no signal, return the max range

    def update_point_cloud(self, strength, angle_resolution=1, vertical_angle_resolution=1):
        """
        Incrementally update the point cloud with a new sonar data point.
        """
        # Convert the sonar strength to distance
        distance = self.strength_to_distance(strength)

        # Convert polar (distance, angle) to Cartesian (x, y, z)
        angle_rad = math.radians(self.current_angle)
        vertical_angle_rad = math.radians(self.vertical_angle)

        # Calculate the 3D coordinates
        x = distance * math.cos(angle_rad) * math.cos(vertical_angle_rad)
        y = distance * math.sin(angle_rad) * math.cos(vertical_angle_rad)
        z = distance * math.sin(vertical_angle_rad)

        # Add the new point to the point cloud
        self.point_cloud.append([x, y, z])

        # Increment the angle for the next data point
        self.current_angle = (self.current_angle + angle_resolution) % 360
        # Adjust this based on your beamwidth
        self.vertical_angle = (self.vertical_angle +
                               vertical_angle_resolution) % 25

    def get_point_cloud(self):
        """
        Return the current point cloud as a NumPy array.
        """
        return np.array(self.point_cloud)


class PingManager:
    def __init__(self, baudrate, device=None, udp=None):
        self.device = device
        self.baudrate = baudrate
        self.udp = udp
        self.my_ping = Ping360()
        if self.device is not None:
            self.my_ping.connect_serial(self.device, self.baudrate)
        elif self.udp is not None:
            (host, port) = self.udp.split(':')
            self.my_ping.connect_udp(host, int(port))

        try:
            self.my_ping.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Ping: {e}!")

        # Create an instance of the point cloud manager
        self.sonar_point_cloud_manager = IncrementalSonarPointCloudManager()

    async def get_ping_data(self):
        """
        Gather and process ping data, updating the point cloud incrementally.
        """
        data = self.my_ping.get_device_data()
        sonar_data = SonarData(
            angle=data['angle'],
            transmit_duration=data['transmit_duration'],
            sample_period=data['sample_period'],
            number_of_samples=data['number_of_samples'],
            data=list(data['data'])  # sonar strength values
        )

        # Update point cloud for each strength value in the sonar data
        for strength in sonar_data.data:
            self.sonar_point_cloud_manager.update_point_cloud(strength)

        return sonar_data

    async def gather_ping_data(self):
        """
        Continuously gather sonar data and update point cloud.
        """
        sonar_data = await self.get_ping_data()
        # You can process the point cloud here or store it
        current_point_cloud = self.sonar_point_cloud_manager.get_point_cloud()
        # Use the point cloud for any additional processing
        logger.info(
            f"Current point cloud has {len(current_point_cloud)} points.")
