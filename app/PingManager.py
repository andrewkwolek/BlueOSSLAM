from brping import definitions
from brping import Ping360
from loguru import logger

import time

from typedefs import SonarData


class PingManager():
    def __init__(self, baudrate, device=None, udp=None):
        self.gathering = False
        self.device = device
        self.baudrate = baudrate
        self.udp = udp
        self.my_ping = Ping360()
        if self.device is not None:
            self.my_ping.connect_serial(self.device, self.baudrate)
        elif self.udp is not None:
            (host, port) = self.udp.split(':')
            self.my_ping.connect_udp(host, int(port))

        if self.my_ping.initialize() is False:
            logger.error("Failed to initialize Ping!")

    async def get_ping_data(self):
        data = self.my_ping.get_auto_device_data()
        sonar_data = SonarData(
            angle=data['angle'],
            transmit_duration=data['transmit_duration'],
            sample_period=data['sample_period'],
            start_angle=data['start_angle'],
            stop_angle=data['stop_angle'],
            number_of_samples=data['number_of_samples'],
            data_length=data['data_length'],
            data=data['data']
        )

        return sonar_data

    async def gather_ping_data(self):
        while self.gathering:
            return self.get_ping_data()
