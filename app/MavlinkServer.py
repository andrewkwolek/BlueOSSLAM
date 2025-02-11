import asyncio
import socket

from MavlinkUDP import UDPMavlinkProtocol


class UDPMavlinkServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.loop = asyncio.get_event_loop()

    async def start(self):
        # Create UDP socket and bind to address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

        # Create a asyncio transport for non-blocking I/O
        self.transport, self.protocol = await self.loop.create_datagram_endpoint(
            lambda: UDPMavlinkProtocol(self.sock), local_addr=(self.host, self.port)
        )
        print(f"Listening for MAVLink data on {self.host}:{self.port}")

    async def stop(self):
        # Clean up UDP server
        self.sock.close()
