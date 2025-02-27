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

    async def extract_features(self, sonar_data, bearings, range_resolution):
        '''Process sonar data and extract features using CFAR'''
        img = sonar_data

        # CFAR Detection
        peaks = self.detector.detect(img, self.alg)
        peaks &= img > self.threshold  # Apply additional thresholding if necessary

        self.cfar_polar = peaks

        # Number of peaks detected
        logger.debug(f"Peaks detected: {np.sum(peaks)}")
        logger.debug(f"Peaks matrix shape: {peaks.shape}")

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

        return np.array(points)  # Point cloud in Cartesian coordinates

    def get_cfar(self):
        return self.cfar_polar
