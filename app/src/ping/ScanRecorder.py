from datetime import datetime
import h5py
import time
import os

from loguru import logger

from settings import SONAR_FILEPATH


class SonarRecorder:
    def __init__(self):
        self.file = None
        self.is_recording = False
        os.makedirs(SONAR_FILEPATH, exist_ok=True)

    def start_recording(self):
        # Open the HDF5 file for writing/appending
        # 'a' mode to append data if the file exists
        logger.info("Start recording sonar.")
        if os.path.exists(SONAR_FILEPATH):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.filename = f"sonar_data_{timestamp}_%03d.h5"
            self.filepath = os.path.join(SONAR_FILEPATH, self.filename)
            self.file = h5py.File(self.filepath, 'a')
            self.is_recording = True

    def stop_recording(self):
        # Close the file when done
        logger.info("Stop recording sonar.")
        if self.file:
            self.file.close()
            self.file = None
            self.is_recording = False

    def save_scan(self, scan):
        if self.is_recording:
            timestamp = int(time.time())
            # Save the scan under a group named by the timestamp
            self.file.create_dataset(f'scan_{timestamp}', data=scan)
        else:
            pass
