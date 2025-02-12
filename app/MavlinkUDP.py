from asyncio import DatagramProtocol
from loguru import logger
from pymavlink import mavutil

from Processor import Processor
from typedefs import MavlinkMessage


class MavlinkUDPProtocol(DatagramProtocol):
    def __init__(self, data_processor: Processor):
        self.data_processor = data_processor  # You can store data_manager to store data
        self.mav = mavutil.mavserial(None)

    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP connection established")

    def datagram_received(self, data, addr):
        """ This method is called when a UDP packet is received """
        logger.debug(f"Received UDP packet from {addr}")

        # You can store the data in your data manager or any other class
        # self.data_manager.process_udp_data(data, addr)
        self.mav.recv(data)
        msg = self.mav.recv_match()

        if msg:
            msg_type = msg.get_type()

            self.data_processor.write_sensor_buffer(msg_type, msg)

    def error_received(self, exc):
        logger.error(f"Error receiving data: {exc}")

    def connection_lost(self, exc):
        logger.info("UDP connection lost")
