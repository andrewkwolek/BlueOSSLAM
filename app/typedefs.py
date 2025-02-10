from enum import Enum
from pydantic import BaseModel


class MavlinkMessage(str, Enum):
    ATTITUDE = "ATTITUDE"
    GLOBAL_POSITION_INT = "GLOBAL_POSITION_INT"
    SCALED_IMU = "SCALED_IMU2"  # Actual ROV may differ
    RAW_IMU = "RAW_IMU"


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


class SLAMData(BaseModel):
    gps_data: GPSData
    attitude_data: AttitudeData
    imu_data: IMUData


class SonarData(BaseModel):
    angle: int
    transmit_duration: int
    sample_period: int
    start_angle: int
    stop_angle: int
    number_of_samples: int
    data_length: int
    data: list
