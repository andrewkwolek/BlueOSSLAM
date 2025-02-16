import asyncio
from collections import deque
from loguru import logger
from pymavlink import mavutil

from PingManager import PingManager
from DataManager import DataManager

from typedefs import MavlinkMessage


class SensorBuffer:
    def __init__(self, max_size, type):
        self.buffer = deque(maxlen=max_size)
        self.lock = asyncio.Lock()
        self.type = type

    async def add_data(self, data):
        async with self.lock:
            self.buffer.append(data)
            # logger.debug(f"Updated {self.type} buffer.")

    async def get_latest_data(self):
        async with self.lock:
            return self.buffer[-1] if self.buffer else None

    async def get_data_near_timestamp(self, target_time):
        """Return the closest data to the target timestamp."""
        async with self.lock:
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
        self.ping_manager = PingManager(device, baudrate, udp)

        self.mav = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
        logger.info("Mavlink connection established.")

        self.imu_buffer = SensorBuffer(10, MavlinkMessage.RAW_IMU)
        self.attitude_buffer = SensorBuffer(10, MavlinkMessage.ATTITUDE)
        self.gps_buffer = SensorBuffer(10, MavlinkMessage.GLOBAL_POSITION_INT)
        self.pressure_buffer = SensorBuffer(10, MavlinkMessage.SCALED_PRESSURE)
        self.servo_buffer = SensorBuffer(10, MavlinkMessage.SERVO_OUTPUT_RAW)

    async def write_gps_buffer_rest(self):
        while True:
            data = await self.data_manager.get_gps_data()
            await self.gps_buffer.add_data(data)
            # print(f"Added gps data: {data}")
            await asyncio.sleep(0)

    async def write_imu_buffer_rest(self):
        while True:
            data = await self.data_manager.get_imu_data()
            await self.imu_buffer.add_data(data)
            # print(f"Added imu data: {data}")
            await asyncio.sleep(0)

    async def write_attitude_buffer_rest(self):
        while True:
            data = await self.data_manager.get_attitude_data()
            await self.attitude_buffer.add_data(data)
            # print(f"Added attitude data: {data}")
            await asyncio.sleep(0)

    async def write_pressure_buffer_rest(self):
        while True:
            data = await self.data_manager.get_pressure_data()
            await self.pressure_buffer.add_data(data)
            # print(f"Added pressure data: {data}")
            await asyncio.sleep(0)

    async def receive_mavlink_data(self):
        while True:
            msg = self.mav.recv_match()
            if msg:
                await self.write_sensor_buffer(msg.get_type(), msg.to_dict())
            await asyncio.sleep(0)

    async def write_sensor_buffer(self, msg_type, msg):
        if msg_type == MavlinkMessage.RAW_IMU:
            await self.imu_buffer.add_data(msg)
        elif msg_type == MavlinkMessage.ATTITUDE:
            await self.attitude_buffer.add_data(msg)
        elif msg_type == MavlinkMessage.GLOBAL_POSITION_INT:
            await self.gps_buffer.add_data(msg)
        elif msg_type == MavlinkMessage.SCALED_PRESSURE:
            await self.pressure_buffer.add_data(msg)
        elif msg_type == MavlinkMessage.SERVO_OUTPUT_RAW:
            await self.servo_buffer.add_data(msg)

    async def receive_sonar_data(self):
        while True:
            await self.ping_manager.gather_ping_data()
            await asyncio.sleep(0)
