import os
import requests
from loguru import logger


class PositionData():
    def __init__(self, alt, lat, lon):
        self.altitude = alt
        self.latitude = lat
        self.longitude = lon


class NavigatorManager():
    def __init__(self) -> None:
        self.url = "http://localhost:6040/mavlink/vehicles/1/components/1/messages"
        self.gps = "GLOBAL_POSITION_INT"
        self.rpy = "ATTITUDE"
        self.position_data = []

    def get_gps_data(self):
        path = os.path.join(self.url, self.gps)
        try:
            gps_response = requests.get(path, timeout=1)
            data = gps_response.json()

            temp_pos = PositionData()
            temp_pos.altitude = data['message']['alt']
            logger.info(f"Altitude: {temp_pos.altitude}")
            temp_pos.latitude = data['message']['lat']
            temp_pos.longitude = data['message']['lon']

            self.position_data.append(temp_pos)
            logger.info("GPS response received.")
            return temp_pos

        except requests.RequestException as e:
            logger.error(f"Could not get GPS response {e}.")
