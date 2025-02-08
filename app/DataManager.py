import os
import requests
from loguru import logger
from pydantic import BaseModel


class PositionData(BaseModel):
    altitude: float
    latitude: float
    longitude: float


class NavigatorManager():
    def __init__(self) -> None:
        self.url = "http://host.docker.internal:6040/v1/mavlink/vehicles/1/components/1/messages"
        self.gps = "GLOBAL_POSITION_INT"
        self.rpy = "ATTITUDE"
        self.position_data = []

    def get_gps_data(self):
        path = os.path.join(self.url, self.gps)
        try:
            gps_response = requests.get(path, timeout=1)
            data = gps_response.json()

            temp_pos = PositionData(
                altitude=data['message']['alt'],
                latitude=data['message']['lat'],
                longitude=data['message']['lon']
            )

            self.position_data.append(temp_pos)
            logger.info("GPS response received.")
            return temp_pos

        except requests.RequestException as e:
            logger.error(f"Could not get GPS response {e}.")
