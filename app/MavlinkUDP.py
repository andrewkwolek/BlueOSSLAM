from asyncio import DatagramProtocol
from loguru import logger


class MavlinkUDPProtocol(DatagramProtocol):
    def __init__(self, data_manager):
        self.data_manager = data_manager  # You can store data_manager to store data

    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP connection established")

    def datagram_received(self, data, addr):
        """ This method is called when a UDP packet is received """
        logger.debug(f"Received UDP packet from {addr}")

        # You can store the data in your data manager or any other class
        # self.data_manager.process_udp_data(data, addr)

    def error_received(self, exc):
        logger.error(f"Error receiving data: {exc}")

    def connection_lost(self, exc):
        logger.info("UDP connection lost")
