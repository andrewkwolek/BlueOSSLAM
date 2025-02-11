from pymavlink import mavutil
from loguru import logger


class MavlinkUDPProtocol:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        # Using None for now, will parse raw data
        self.mav = mavutil.mavlink_connection('udp:host.docker.internal:14550')

    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP connection established")

    def datagram_received(self, data, addr):
        """
        This method will be called when a UDP packet is received.
        It parses the incoming MAVLink data and processes it.
        """
        try:
            # The connection object expects the data in bytes. We can use `mavutil.mavlink_connection`
            # to parse the raw MAVLink data from the UDP packet.
            self.mav.parse(data)

            # Check if the message was valid
            while self.mav.messages:
                msg = self.mav.messages.pop(0)
                logger.debug(f"Received MAVLink message: {msg}")

                # Process and store the message (for example, storing in data_manager)
                # self.data_manager.store_data(msg)

        except Exception as e:
            logger.error(f"Error processing MAVLink data: {e}")

    def error_received(self, exc):
        logger.error(f"Error received: {exc}")

    def connection_lost(self, exc):
        logger.info("UDP connection lost")
