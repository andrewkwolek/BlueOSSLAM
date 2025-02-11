from enum import Enum
from pydantic import BaseModel

from typing import Any


class MavlinkMessage(str, Enum):
    ATTITUDE = "ATTITUDE"
    GLOBAL_POSITION_INT = "GLOBAL_POSITION_INT"
    SCALED_IMU = "SCALED_IMU2"  # Actual ROV may differ
    RAW_IMU = "RAW_IMU"
    SCALED_PRESSURE = "SCALED_PRESSURE"


class GPSData(BaseModel):
    timestamp: int
    altitude: float
    latitude: float
    longitude: float


class AttitudeData(BaseModel):
    timestamp: int
    roll: float  # Rotation about X (Straight)
    pitch: float  # Rotation about Y (Right)
    yaw: float  # Rotation about Z (Down)
    pitch_speed: float
    roll_speed: float
    yaw_speed: float


class IMUData(BaseModel):
    timestamp: int
    x_acc: float
    x_gyro: float
    y_acc: float
    y_gyro: float
    z_acc: float
    z_gyro: float


class PressureData(BaseModel):
    timestamp: int
    press_abs: float
    press_diff: float


class LocalizationData(BaseModel):
    timestamp: Any
    gps_data: GPSData
    attitude_data: AttitudeData
    imu_data: IMUData
    pressure_data: PressureData


class SonarData(BaseModel):
    angle: int
    transmit_duration: int
    sample_period: int
    number_of_samples: int
    data: list
