import asyncio
import modern_robotics as mr
import numpy as np

from Processor import Processor


class ROVState:
    def __init__(self, processor: Processor):
        self.data_processor = processor

        self.start_time = processor.data_manager.get_time_data()['timestamp']

        # State vector of ROV
        self.q_rov = np.array([0, 0, 0, 0, 0, 0])
