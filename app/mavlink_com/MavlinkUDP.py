class UDPMavlinkProtocol:
    def __init__(self, sock):
        self.sock = sock

    def connection_made(self, transport):
        print("UDP connection established")

    def datagram_received(self, data, addr):
        # Print received MAVLink data for now (can be processed further)
        print(f"Received data from {addr}: {data}")

    def error_received(self, exc):
        print(f"Error received: {exc}")

    def connection_lost(self, exc):
        print("UDP connection lost")
