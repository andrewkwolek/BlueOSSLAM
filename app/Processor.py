import asyncio
from collections import deque

from PingManager import PingManager
from DataManager import DataManager


class SensorBuffer:
    def __init__(self, max_size):
        self.buffer = deque(maxlen=max_size)

    async def add_data(self, data):
        self.buffer.append(data)

    async def get_latest_data(self):
        return self.buffer[-1] if self.buffer else None

    async def get_data_near_timestamp(self, target_time):
        """Return the closest data to the target timestamp."""
        closest_data = None
        min_time_diff = float('inf')

        for data in self.buffer:
            timestamp = data['timestamp']
            time_diff = abs(target_time - timestamp)
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_data = (timestamp, data)

        return closest_data


class Processor:

    def __init__(self, baudrate, device=None, udp=None):
        self.data_manager = DataManager()
        self.ping_manager = PingManager(baudrate, device, udp)

        self.imu_buffer, self.attitude_buffer, self.gps_buffer, self.pressure_buffer = SensorBuffer(
            10)

    async def write_gps_buffer(self):
        while True:
            data = await self.data_manager.get_gps_data()
            await self.gps_buffer.add_data(data)
            print(f"Added gps data: {data}")
            await asyncio.sleep(0)

    async def write_imu_buffer(self):
        while True:
            data = await self.data_manager.get_imu_data()
            await self.imu_buffer.add_data(data)
            print(f"Added imu data: {data}")
            await asyncio.sleep(0)

    async def write_attitude_buffer(self):
        while True:
            data = await self.data_manager.get_attitude_data()
            await self.attitude_buffer.add_data(data)
            print(f"Added attitude data: {data}")
            await asyncio.sleep(0)

    async def write_pressure_buffer(self):
        while True:
            data = await self.data_manager.get_pressure_data()
            await self.pressure_buffer.add_data(data)
            print(f"Added pressure data: {data}")
            await asyncio.sleep(0)
