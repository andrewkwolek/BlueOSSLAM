from enum import Enum
from pydantic import BaseModel


class MavlinkMessage(str, Enum):
    ATTITUDE = "ATTITUDE"
    GLOBAL_POSITION_INT = "GLOBAL_POSITION_INT"
    SCALED_IMU = "SCALED_IMU2"  # Actual ROV may differ


class GPSData(BaseModel):
    timestamp: float
    altitude: float
    latitude: float
    longitude: float


class AttitudeData(BaseModel):
    timestamp: float
    roll: float  # Rotation about X (Straight)
    pitch: float  # Rotation about Y (Right)
    yaw: float  # Rotation about Z (Down)
    pitch_speed: float
    roll_speed: float
    yaw_speed: float


class IMUData(BaseModel):
    timestamp: float
    x_acc: float
    x_gyro: float
    y_acc: float
    y_gyro: float
    z_acc: float
    z_gyro: float
