import asyncio
import numpy as np


from Processor import Processor
from ping.PingManager import PingManager


class SLAM:
    def __init__(self, processor, ping_manager):
        self.q = None

        self.processor = processor
        self.ping_manager = ping_manager

    def initialize(self):
        pass
