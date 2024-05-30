import copy
import math
import time
from collections import deque
import threading
from dataclasses import dataclass
from enum import Enum

import numpy


class MAVLinkDataType(Enum):
    LOCAL_POSITION = "LOCAL_POSITION_NED"
    GLOBAL_POSITION = "GLOBAL_POSITION_INT"
    ATTITUDE = "ATTITUDE"
    GIMBAL = "GIMBAL_DEVICE_ATTITUDE_STATUS"
    RC = "RC_CHANNELS"
    SERVO = "SERVO_OUTPUT_RAW"


class QueuePipe:
    def __init__(self, max_size=100):
        self._queue = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def size(self):
        with self._lock:
            return len(self._queue)

    def add_data(self, data):
        with self._lock:
            self._queue.append(data)

    def get_data(self, size):
        with self._lock:
            available_size = min(size, len(self._queue))

            return list(self._queue)[:available_size]

    def get_latest(self):
        with self._lock:
            try:
                return self._queue[-1]
            except IndexError:
                return None


@dataclass
class Quaternion:
    w: float
    x: float
    y: float
    z: float

    def __init__(self, source=None, w=None, x=None, y=None, z=None):
        if isinstance(source, (list, tuple)) and len(source) == 4:
            self.w, self.x, self.y, self.z = source
        elif all(v is not None for v in [w, x, y, z]):
            self.w, self.x, self.y, self.z = w, x, y, z
        else:
            raise ValueError("Invalid source for Quaternion, must be a list or tuple with four elements.")

    @classmethod
    def from_euler(cls, roll, pitch, yaw):
        cy = math.cos(yaw / 2)
        sy = math.sin(yaw / 2)
        cp = math.cos(pitch / 2)
        sp = math.sin(pitch / 2)
        cr = math.cos(roll / 2)
        sr = math.sin(roll / 2)

        w = cy * cp * cr + sy * sp * sr
        x = cy * cp * sr - sy * sp * cr
        y = sy * cp * sr + cy * sp * cr
        z = sy * cp * cr - cy * sp * sr

        return cls(w=w, x=x, y=y, z=z)

    @classmethod
    def from_mavlink(cls, attitude):
        return cls.from_euler(
            roll=attitude.roll,
            pitch=attitude.pitch,
            yaw=attitude.yaw
        )

    def to_array(self):
        return [self.w, self.x, self.y, self.z]

    def to_euler(self):
        sinr_cosp = 2 * (self.w * self.x + self.y * self.z)
        cosr_cosp = 1 - 2 * (self.x ** 2 + self.y ** 2)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        sinp = 2 * (self.w * self.y - self.z * self.x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)

        siny_cosp = 2 * (self.w * self.z + self.x * self.y)
        cosy_cosp = 1 - 2 * (self.y ** 2 + self.z ** 2)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw


@dataclass
class LocalPosition:
    timestamp: float
    x: float
    y: float
    z: float
    vx: float = None
    vy: float = None
    vz: float = None

    @classmethod
    def from_mavlink(cls, data):
        return cls(
            timestamp=time.time(),
            x=data.x,
            y=data.y,
            z=data.z,
            vx=data.vx,
            vy=data.vy,
            vz=data.vz
        )

    def to_array(self):
        return self.x, self.y, self.z


@dataclass
class GlobalPosition:
    timestamp: float
    latitude: int
    longitude: int
    altitude: float
    relative_altitude: float
    vx: float
    vy: float
    vz: float
    heading: float

    @classmethod
    def from_mavlink(cls, data):
        return cls(
            timestamp=time.time(),
            latitude=data.lat / 1e7,
            longitude=data.lon / 1e7,
            altitude=data.alt / 1000,
            relative_altitude=data.relative_alt / 1000,
            vx=data.vx / 100,
            vy=data.vy / 100,
            vz=data.vz / 100,
            heading=data.hdg / 100
        )


@dataclass
class Attitude:
    timestamp: float
    roll: float
    pitch: float
    yaw: float
    roll_speed: float = None
    pitch_speed: float = None
    yaw_speed: float = None

    def copy(self):
        return copy.copy(self)

    @classmethod
    def from_mavlink(cls, data):
        return cls(
            timestamp=time.time(),
            roll=data.roll,
            pitch=data.pitch,
            yaw=data.yaw,
            roll_speed=data.rollspeed,
            pitch_speed=data.pitchspeed,
            yaw_speed=data.yawspeed
        )

    def to_degrees(self):
        roll_degrees = math.degrees(self.roll)
        pitch_degrees = math.degrees(self.pitch)
        yaw_degrees = math.degrees(self.yaw)
        roll_speed_degrees = math.degrees(self.roll_speed) if self.roll_speed is not None else None
        pitch_speed_degrees = math.degrees(self.pitch_speed) if self.pitch_speed is not None else None
        yaw_speed_degrees = math.degrees(self.yaw_speed) if self.yaw_speed is not None else None

        return Attitude(
            timestamp=self.timestamp,
            roll=roll_degrees,
            pitch=pitch_degrees,
            yaw=yaw_degrees,
            roll_speed=roll_speed_degrees,
            pitch_speed=pitch_speed_degrees,
            yaw_speed=yaw_speed_degrees
        )

    def to_quaterion(self):
        quaterion = Quaternion.from_euler(
            roll=self.roll,
            pitch=self.pitch,
            yaw=self.yaw
        )

        return quaterion

    def add_offset(self, roll=0, pitch=0, yaw=0):
        self.roll += roll
        self.pitch += pitch
        self.yaw += yaw

        return self

    def transfer_offset(self, roll=0, pitch=0, yaw=0):
        new_attitude = self.copy()

        new_attitude.add_offset(
            roll=roll,
            pitch=pitch,
            yaw=yaw
        )

        return new_attitude


@dataclass
class Gimbal:
    timestamp: float
    flags: int
    quaternion: Quaternion

    def copy(self):
        return copy.copy(self)

    @classmethod
    def from_mavlink(cls, data):
        return cls(
            timestamp=time.time(),
            flags=data.flags,
            quaternion=Quaternion(data.q)
        )


@dataclass
class RCChannels:
    timestamp: float
    channels_count: int
    channels_raw: list
    rssi: int

    def copy(self):
        return copy.copy(self)

    @classmethod
    def from_mavlink(cls, data):
        return cls(
            timestamp=time.time(),
            channels_count=data.chancount,
            channels_raw=[
                data.chan1_raw, data.chan2_raw, data.chan3_raw,
                data.chan4_raw, data.chan5_raw, data.chan6_raw,
                data.chan7_raw, data.chan8_raw, data.chan9_raw,
                data.chan10_raw, data.chan11_raw, data.chan12_raw,
                data.chan13_raw, data.chan14_raw, data.chan15_raw,
                data.chan16_raw, data.chan17_raw, data.chan18_raw
            ],
            rssi=data.rssi
        )


@dataclass
class ServoChannels:
    timestamp: float
    servos_raw: list

    def copy(self):
        return copy.copy(self)

    @classmethod
    def from_mavlink(cls, data):
        return cls(
            timestamp=time.time(),
            servos_raw=[
                data.servo1_raw, data.servo2_raw, data.servo3_raw, data.servo4_raw,
                data.servo5_raw, data.servo6_raw, data.servo7_raw, data.servo8_raw,
                data.servo9_raw, data.servo10_raw, data.servo11_raw, data.servo12_raw,
                data.servo13_raw, data.servo14_raw, data.servo15_raw, data.servo16_raw
            ]
        )
