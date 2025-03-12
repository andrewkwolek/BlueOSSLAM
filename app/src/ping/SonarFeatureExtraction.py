import numpy as np
import cv2
from scipy.interpolate import interp1d
from .CFAR import CFAR  # Your CFAR implementation
from loguru import logger


class SonarFeatureExtraction:
    def __init__(self, Ntc=40, Ngc=10, Pfa=1e-2, rank=None, alg="SOCA", resolution=0.5, threshold=0):
        self.Ntc = Ntc
        self.Ngc = Ngc
        self.Pfa = Pfa
        self.rank = rank
        self.alg = alg
        self.threshold = threshold
        self.resolution = resolution
        # Use your CFAR implementation
        self.detector = CFAR(self.Ntc, self.Ngc, self.Pfa)
        self.map_x = None
        self.map_y = None

        self.cfar_polar = None

    async def create_costmap_in_cartesian(self, sonar_data, bearings, range_resolution):
        '''Create a mesh grid of zeros in Cartesian coordinates from sonar data in polar coordinates'''
        _res = range_resolution
        _height = len(sonar_data) * _res

        if bearings[-1] < bearings[0]:
            bearing_range = 360 - (bearings[0] - bearings[-1])
        else:
            bearing_range = bearings[-1] - bearings[0]
        _width = np.sin(np.radians(bearing_range)) * _height

        # Create a meshgrid for x and y axes based on the range values
        x_range = np.arange(-_width/2, _width/2, _res)
        y_range = np.arange(0, _height, _res)

        X, Y = np.meshgrid(x_range, y_range)

        costmap = np.zeros_like(X, dtype=np.float32)

        return costmap, X, Y

    async def extract_features(self, sonar_data, bearings, range_resolution):
        '''Process sonar data and extract features using CFAR'''
        img = sonar_data

        # CFAR Detection
        peaks = self.detector.detect(img, self.alg)
        peaks &= img > self.threshold  # Apply additional thresholding if necessary

        self.cfar_polar = peaks

        # Get indices of detected peaks
        peak_indices = np.argwhere(peaks)

        # Convert directly to Cartesian coordinates without using remap
        points = []

        # Handle bearings that wrap around 0/360
        if bearings[0] > bearings[-1]:
            # Adjust bearings that cross the 0/360 boundary
            adjusted_bearings = bearings.copy()
            for adjusted_bearing in adjusted_bearings:
                if adjusted_bearing < 180:
                    adjusted_bearing += 360
        else:
            adjusted_bearings = bearings

        # For each peak, calculate its Cartesian coordinates
        for peak in peak_indices:
            range_idx, azimuth_idx = peak

            # Get the range in meters
            range_m = range_idx * range_resolution

            # Get the bearing angle in radians
            bearing_deg = adjusted_bearings[azimuth_idx % len(bearings)]
            if bearing_deg > 360:
                bearing_deg -= 360
            bearing_rad = np.radians(bearing_deg)

            # Convert to Cartesian
            # Note: Using convention where 0 degrees = positive y-axis
            y = range_m * np.cos(bearing_rad)
            x = range_m * np.sin(bearing_rad)

            points.append([y, x])

        if not points:
            return np.empty((0, 2))

        costmap, X, Y = await self.create_costmap_in_cartesian(
            sonar_data, bearings, range_resolution)

        for point in points:
            # Convert polar (r, theta) to Cartesian (x, y)
            x = point[1]  # X-coordinate in meters
            y = point[0]  # Y-coordinate in meters

            # Find the closest indices on the mesh grid
            x_idx = np.abs(X[0] - x).argmin()  # Find closest X index
            y_idx = np.abs(Y[:, 0] - y).argmin()  # Find closest Y index

            # Mark the detected point on the costmap
            costmap[y_idx, x_idx] = 1  # Or increment based on detection count

        return costmap, X, Y

    def get_cfar(self):
        return self.cfar_polar

    async def update_cfar_parameters(self, Ntc, Ngc, Pfa, rank=None, alg=None, threshold=None):
        """
        Update CFAR parameters without recreating the detector.

        Args:
            Ntc (int): Number of training cells (must be even)
            Ngc (int): Number of guard cells (must be even)
            Pfa (float): Probability of false alarm (0-1)
            rank (int, optional): Rank parameter for OS-CFAR
            alg (str, optional): CFAR algorithm type
            threshold (float, optional): Additional threshold value
        """
        # Update instance variables
        self.Ntc = Ntc
        self.Ngc = Ngc
        self.Pfa = Pfa

        if rank is not None:
            self.rank = rank

        if alg is not None:
            self.alg = alg

        if threshold is not None:
            self.threshold = threshold

        # Update the CFAR detector
        self.detector = CFAR(self.Ntc, self.Ngc, self.Pfa, self.rank)

        return True
