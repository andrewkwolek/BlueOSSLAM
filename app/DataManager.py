import asyncio
import os
import pandas as pd
import requests
from datetime import datetime
from loguru import logger

from typedefs import AttitudeData, GPSData, IMUData, SLAMData, MavlinkMessage
from settings import DATA_FILEPATH


class DataManager():
    def __init__(self) -> None:
        self.url = "http://host.docker.internal:6040/v1/mavlink/vehicles/1/components/1/messages"
        self.data = pd.DataFrame(
            columns=[
                "timestamp",
                "latitude",
                "longitude",
                "altitude",
                "x_acc",
                "y_acc",
                "z_acc",
                "x_gyro",
                "y_gyro",
                "z_gyro",
                "roll",
                "pitch",
                "yaw"
            ]
        )
        self.is_recording = False
        self.recording_task = None

    async def start_recording(self):
        if self.is_recording:
            logger.warning("Already recording!")
            return

        self.data = self.data.iloc[0:0]
        self.is_recording = True
        logger.info("Recording started.")

        # self.recording_task = asyncio.create_task()

    async def stop_recording(self):
        if not self.is_recording:
            logger.warning("No recording in progress!")
            return

        self.is_recording = False
        logger.info("Recording stopped.")

        if os.makedirs(DATA_FILEPATH, exist_ok=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"slam_data_{timestamp}_%03d.csv"
            filepath = os.path.join(DATA_FILEPATH, filename)

            self.data.to_csv(filepath, index=False)
            logger.info(f"Data saved to {filename}")
        else:
            logger.warning(f"File path {DATA_FILEPATH} does not exist.")

    async def get_gps_data(self):
        path = os.path.join(self.url, MavlinkMessage.GLOBAL_POSITION_INT)
        try:
            gps_response = requests.get(path, timeout=1)
            msg = gps_response.json()['message']

            temp_pos = GPSData(
                timestamp=msg['time_boot_ms'],
                altitude=msg['alt'],
                latitude=msg['lat'],
                longitude=msg['lon']
            )

            logger.info("GPS response received.")
            return temp_pos

        except requests.RequestException as e:
            logger.error(f"Could not get GPS response {e}.")

    async def get_imu_data(self):
        path = os.path.join(self.url, MavlinkMessage.SCALED_IMU)
        try:
            gps_response = requests.get(path, timeout=1)
            msg = gps_response.json()['message']

            temp_pos = IMUData(
                timestamp=msg['time_boot_ms'],
                x_acc=msg['xacc'],
                x_gyro=msg['xgyro'],
                y_acc=msg['yacc'],
                y_gyro=msg['ygyro'],
                z_acc=msg['zacc'],
                z_gyro=msg['zgyro']
            )

            logger.info("IMU response received.")
            return temp_pos

        except requests.RequestException as e:
            logger.error(f"Could not get IMU response {e}.")

    async def get_attitude_data(self):
        path = os.path.join(self.url, MavlinkMessage.ATTITUDE)
        try:
            gps_response = requests.get(path, timeout=1)
            msg = gps_response.json()['message']

            temp_pos = AttitudeData(
                timestamp=msg['time_boot_ms'],
                roll=msg['roll'],
                pitch=msg['pitch'],
                yaw=msg['yaw'],
                roll_speed=msg['rollspeed'],
                pitch_speed=msg['pitchspeed'],
                yaw_speed=msg['yawspeed']
            )

            logger.info("Attitude response received.")
            return temp_pos

        except requests.RequestException as e:
            logger.error(f"Could not get attitude response {e}.")

    async def get_all_data(self):
        gps = await self.get_gps_data()
        imu = await self.get_imu_data()
        att = await self.get_attitude_data()

        slam_data = SLAMData(
            gps_data=gps,
            imu_data=imu,
            attitude_data=att
        )

        return slam_data

    async def record_data(self):
        while self.is_recording:
            try:
                gps_data = await self.get_gps_data()
                imu_data = await self.get_imu_data()
                attitude_data = await self.get_attitude_data()

                self.data.loc[-1] = [datetime.now(),
                                     gps_data.latitude,
                                     gps_data.longitude,
                                     gps_data.altitude,
                                     imu_data.x_acc,
                                     imu_data.y_acc,
                                     imu_data.z_acc,
                                     imu_data.x_gyro,
                                     imu_data.y_gyro,
                                     imu_data.z_gyro,
                                     attitude_data.roll,
                                     attitude_data.pitch,
                                     attitude_data.yaw]
            except Exception as e:
                logger.error(f"Could not get attitude response {e}.")
