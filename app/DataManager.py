import os
import requests
from loguru import logger

from typedefs import AttitudeData, GPSData, IMUData, SLAMData, MavlinkMessage


class DataManager():
    def __init__(self) -> None:
        self.url = "http://host.docker.internal:6040/v1/mavlink/vehicles/1/components/1/messages"
        self.data = []
        self.is_recording = False

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
