from asyncio import DatagramProtocol
from loguru import logger


class MavlinkUDPProtocol(DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"Connected to UDP server")

    def datagram_received(self, data, addr):
        # Handle incoming data (MAVLink messages or whatever your protocol is)
        logger.debug(f"Received data: {data} from {addr}")
        # You can now process this data, e.g., parse MAVLink messages
        # Example: Print data
        print(f"Received {data} from {addr}")

    def error_received(self, exc):
        logger.error(f"Error received: {exc}")

    def connection_lost(self, exc):
        logger.info("Connection lost")
