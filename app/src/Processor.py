import asyncio
from collections import deque
from typing import Dict, Any, Optional, List, Tuple
import time
from loguru import logger
from pymavlink import mavutil

from ping.PingManager import PingManager
from mavlink.DataManager import DataManager
from typedefs import MavlinkMessage


class SensorBuffer:
    """
    Thread-safe buffer for storing sensor data with timestamp-based retrieval.

    Provides a circular buffer with asynchronous access methods for storing
    and retrieving sensor data, with the ability to find data closest to a 
    specific timestamp.
    """

    def __init__(self, max_size: int, data_type: str):
        """
        Initialize the sensor buffer.

        Args:
            max_size: Maximum number of data points to store
            data_type: Type of data stored in this buffer (for logging)
        """
        self.buffer = deque(maxlen=max_size)
        self.lock = asyncio.Lock()
        self.type = data_type

    async def add_data(self, data: Dict[str, Any]) -> None:
        """
        Add a data point to the buffer thread-safely.

        Args:
            data: Data point to add to the buffer
        """
        if data is None:
            return

        async with self.lock:
            self.buffer.append(data)

    async def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent data point from the buffer.

        Returns:
            The most recent data point, or None if buffer is empty
        """
        async with self.lock:
            return self.buffer[-1] if self.buffer else None

    async def get_data_near_timestamp(self, target_time: int) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Return the closest data to the target timestamp.

        Args:
            target_time: Target timestamp to find closest data for

        Returns:
            Tuple of (timestamp, data) for closest match, or None if buffer is empty
        """
        async with self.lock:
            if not self.buffer:
                return None

            closest_data = None
            min_time_diff = float('inf')

            for data in self.buffer:
                if 'timestamp' not in data:
                    continue

                timestamp = data['timestamp']
                time_diff = abs(target_time - timestamp)

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_data = (timestamp, data)

            return closest_data

    async def clear(self) -> None:
        """Clear all data from the buffer."""
        async with self.lock:
            self.buffer.clear()

    def __len__(self) -> int:
        """Return the current number of items in the buffer."""
        return len(self.buffer)


class Processor:
    """
    Main sensor data processor for the SLAM system.

    Manages connections to sensors, buffers incoming data, and provides
    methods to access synchronized sensor data.
    """

    def __init__(self):
        """Initialize the processor with data managers and sensor buffers."""
        self.data_manager = DataManager()

        # Initialize MAVLink connection
        try:
            self.mav = mavutil.mavlink_connection('udpin:0.0.0.0:14555')
            logger.info("MAVLink connection established")
        except Exception as e:
            logger.error(f"Failed to establish MAVLink connection: {e}")
            self.mav = None

        # Initialize sensor data buffers
        self.imu_buffer = SensorBuffer(10, MavlinkMessage.RAW_IMU)
        self.attitude_buffer = SensorBuffer(10, MavlinkMessage.ATTITUDE)
        self.gps_buffer = SensorBuffer(10, MavlinkMessage.GLOBAL_POSITION_INT)
        self.pressure_buffer = SensorBuffer(10, MavlinkMessage.SCALED_PRESSURE)
        self.servo_buffer = SensorBuffer(10, MavlinkMessage.SERVO_OUTPUT_RAW)

        # Tasks
        self.tasks = []
        self.running = False

    async def start(self) -> None:
        """Start all data collection tasks."""
        if self.running:
            logger.warning("Processor is already running")
            return

        self.running = True

        # Start data collection tasks
        if self.mav:
            self.tasks.append(asyncio.create_task(self.receive_mavlink_data()))

        self.tasks.extend([
            asyncio.create_task(self.write_gps_buffer_rest()),
            asyncio.create_task(self.write_imu_buffer_rest()),
            asyncio.create_task(self.write_attitude_buffer_rest()),
            asyncio.create_task(self.write_pressure_buffer_rest())
        ])

        logger.info("Processor started all data collection tasks")

    async def stop(self) -> None:
        """Stop all data collection tasks."""
        if not self.running:
            return

        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks.clear()
        logger.info("Processor stopped all data collection tasks")

    async def write_gps_buffer_rest(self) -> None:
        """Continuously poll and store GPS data from REST API."""
        while self.running:
            try:
                data = await self.data_manager.get_gps_data()
                await self.gps_buffer.add_data(data)
            except Exception as e:
                logger.error(f"Error getting GPS data: {e}")

            await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging

    async def write_imu_buffer_rest(self) -> None:
        """Continuously poll and store IMU data from REST API."""
        while self.running:
            try:
                data = await self.data_manager.get_imu_data()
                await self.imu_buffer.add_data(data)
            except Exception as e:
                logger.error(f"Error getting IMU data: {e}")

            await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging

    async def write_attitude_buffer_rest(self) -> None:
        """Continuously poll and store attitude data from REST API."""
        while self.running:
            try:
                data = await self.data_manager.get_attitude_data()
                await self.attitude_buffer.add_data(data)
            except Exception as e:
                logger.error(f"Error getting attitude data: {e}")

            await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging

    async def write_pressure_buffer_rest(self) -> None:
        """Continuously poll and store pressure data from REST API."""
        while self.running:
            try:
                data = await self.data_manager.get_pressure_data()
                await self.pressure_buffer.add_data(data)
            except Exception as e:
                logger.error(f"Error getting pressure data: {e}")

            await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging

    async def receive_mavlink_data(self) -> None:
        """Receive and process MAVLink messages from the vehicle."""
        if not self.mav:
            logger.error("MAVLink connection not available")
            return

        while self.running:
            try:
                msg = self.mav.recv_match(blocking=False)
                if msg:
                    await self.write_sensor_buffer(msg.get_type(), msg.to_dict())
            except Exception as e:
                logger.error(f"Error receiving MAVLink data: {e}")

            await asyncio.sleep(0.01)  # Small delay to prevent CPU hogging

    async def write_sensor_buffer(self, msg_type: str, msg: Dict[str, Any]) -> None:
        """
        Route incoming MAVLink messages to the appropriate sensor buffer.

        Args:
            msg_type: Type of MAVLink message
            msg: Message data as dictionary
        """
        try:
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
        except Exception as e:
            logger.error(f"Error writing to sensor buffer for {msg_type}: {e}")

    async def get_synchronized_data(self, base_timestamp: int) -> Dict[str, Any]:
        """
        Get sensor data synchronized around a specific timestamp.

        Args:
            base_timestamp: Base timestamp to synchronize around

        Returns:
            Dictionary of synchronized sensor data
        """
        # Get data closest to the timestamp from each buffer
        gps_data = await self.gps_buffer.get_data_near_timestamp(base_timestamp)
        imu_data = await self.imu_buffer.get_data_near_timestamp(base_timestamp)
        attitude_data = await self.attitude_buffer.get_data_near_timestamp(base_timestamp)
        pressure_data = await self.pressure_buffer.get_data_near_timestamp(base_timestamp)

        # Pack into a single dictionary
        return {
            "timestamp": base_timestamp,
            "gps": gps_data[1] if gps_data else None,
            "imu": imu_data[1] if imu_data else None,
            "attitude": attitude_data[1] if attitude_data else None,
            "pressure": pressure_data[1] if pressure_data else None,
        }

    async def get_buffer_stats(self) -> Dict[str, int]:
        """
        Get statistics about the current buffer states.

        Returns:
            Dictionary with buffer sizes
        """
        return {
            "imu": len(self.imu_buffer),
            "attitude": len(self.attitude_buffer),
            "gps": len(self.gps_buffer),
            "pressure": len(self.pressure_buffer),
            "servo": len(self.servo_buffer),
        }
