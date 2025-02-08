import requests
from loguru import logger


class SonarManager():
    def __init__(self) -> None:
        self.url = "http://loclhost:6040/mavlink/vehicles/1/components/194/messages/DISTANCE_SENSOR"

    async def get_sonar_data(self):
        distance_response = requests.get(self.url)
        logger.info()
