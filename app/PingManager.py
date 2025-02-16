import asyncio
import numpy as np
from brping import Ping360
from brping import definitions
from typing import Optional, Dict
from loguru import logger
from typedefs import SonarData
import time


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
                self.data = m.unpack_msg_data()
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
