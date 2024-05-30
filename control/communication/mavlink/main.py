import math
import time
from mavlink import MAVLinkController, DataAcquisitionThread
from mavlink.data import QueuePipe, Attitude, GlobalPosition, LocalPosition
from mavlink.processor import DataProcessor, GimbalProcessor, GlobalPositionProcessor, AttitudeProcessor
from pymavlink import mavutil
from mavlink.data import MAVLinkDataType, Gimbal, RCChannels, ServoChannels


mavlink_connection = MAVLinkController("udp:0.0.0.0:14550")

attitude_processor = AttitudeProcessor()
gimbal_processor = GimbalProcessor()

acquisition_thread = DataAcquisitionThread(mavlink_connection, [attitude_processor, gimbal_processor])
acquisition_thread.start()

for i in range(0, 90, 10):
    latest_data = gimbal_processor.queue.get_latest()
    if latest_data:
        print("GIMBAL", [math.degrees(axis) for axis in latest_data.quaternion.to_euler()])

    mavlink_connection.gimbal.set_angles(
        roll=0,
        pitch=0,
        yaw=i
    )

    time.sleep(0.5)

mavlink_connection.gimbal.set_roi_location(-35.36, 149.164, 583)
time.sleep(1)
mavlink_connection.gimbal.disable_roi()
