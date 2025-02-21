import numpy as np
import cv2
from scipy.interpolate import interp1d
from CFAR import CFAR  # Your CFAR implementation
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

    async def generate_map_xy(self, bearings, range_resolution, num_ranges):
        '''Generate a mesh grid map for remapping sonar image from polar to Cartesian'''
        _res = range_resolution
        _height = num_ranges * _res
        _rows = num_ranges

        if bearings[-1] < bearings[0]:
            bearing_range = 360 - (bearings[-1] - bearings[0])
        else:
            bearing_range = bearings[-1] - bearings[0]
        _width = np.sin(np.radians(bearing_range)) * _height
        _cols = int(np.ceil(_width / _res))

        bearings = np.radians(bearings)
        f_bearings = interp1d(
            bearings, range(len(bearings)), kind="linear", bounds_error=False, fill_value=-1
        )

        # Meshgrid for remapping polar to Cartesian
        XX, YY = np.meshgrid(range(_cols), range(_rows))
        x = _res * (_rows - YY)
        y = _res * (-_cols / 2.0 + XX + 0.5)
        b = np.arctan2(y, x)
        r = np.sqrt(x ** 2 + y ** 2)

        self.map_y = np.asarray(r / _res, dtype=np.float32)
        self.map_x = np.asarray(f_bearings(b), dtype=np.float32)

        logger.debug(
            f"map_x shape: {self.map_x.shape}, map_y shape: {self.map_y.shape}")
        print(f"XX shape: {XX.shape}, YY shape: {YY.shape}")

    async def extract_features(self, sonar_data, bearings, range_resolution):
        '''Process sonar data and extract features using CFAR'''
        img = sonar_data

        if self.map_x is None or self.map_y is None:
            await self.generate_map_xy(bearings, range_resolution, len(sonar_data))

        # CFAR Detection
        peaks = self.detector.detect(img, self.alg)
        peaks &= img > self.threshold  # Apply additional thresholding if necessary

        logger.debug(
            f"map_x shape: {self.map_x.shape}, map_y shape: {self.map_y.shape}")

        # Convert to Cartesian coordinates
        peaks_cartesian = cv2.remap(
            peaks, self.map_x, self.map_y, cv2.INTER_LINEAR)
        locs = np.c_[np.nonzero(peaks_cartesian)]

        # Convert polar to Cartesian
        x = locs[:, 1] - self.map_x.shape[1] / 2
        x = (-1 *
             ((x / float(self.map_x.shape[1] / 2)) * (self.map_y.max() / 2)))
        y = (-1 * (locs[:, 0] / float(self.map_y.shape[0]))
             * self.map_y.max()) + self.map_y.max()

        points = np.column_stack((y, x))
        return points  # Point cloud in Cartesian coordinates
