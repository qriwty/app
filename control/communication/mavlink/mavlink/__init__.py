import time
import threading
from .data import Quaternion

from pymavlink import mavutil


class MAVLinkController:
    def __init__(self, device):
        self.lock = threading.Lock()
        self.boot_time = None
        self.connection = self.create_connection(device)
        self.gimbal = GimbalController(self)

    def create_connection(self, url):
        self.connection = mavutil.mavlink_connection(url)
        self.connection.wait_heartbeat()
        self.boot_time = time.time()

        return self.connection

    def encode_command_long(self, command, flag, *params):
        return self.connection.mav.command_long_encode(
            self.connection.target_system,
            self.connection.target_component,
            command,
            flag,
            *params
        )

    def encode_command_int(self, frame, command, *params):
        return self.connection.mav.command_int_encode(
            self.connection.target_system,
            self.connection.target_component,
            frame,
            command,
            0,
            0,
            *params
        )

    def send_attitude(self, attitude):
        attitude_quaterion = Quaternion.from_euler(attitude.roll, attitude.pitch, attitude.yaw)

        byte_mask = 0b00000111

        composed_attitude = self.connection.mav.set_attitude_target_encode(
            0,
            self.connection.target_system,
            self.connection.target_component,
            byte_mask,
            attitude_quaterion,
            0, 0, 0, thrust=0.5
        )

        self.send_packet(composed_attitude)

    def send_control(self, control_values):
        composed_control = self.connection.mav.rc_channels_override_encode(
            self.connection.target_system,
            self.connection.target_component,
            *control_values
        )

        self.send_packet(composed_control)

    def send_packet(self, message):
        with self.lock:
            self.connection.mav.send(message)

    def receive_packet(self, packet_type):
        with self.lock:
            message = self.connection.recv_match(type=packet_type, blocking=True)

            return message

    def receive_data(self):
        with self.lock:
            message = self.connection.recv_match(blocking=True)

            return message


class GimbalController:
    def __init__(self, mavlink_controller: MAVLinkController):
        self.mavlink_controller = mavlink_controller

    def set_angles(self, roll=0, pitch=0, yaw=0):
        command = self.mavlink_controller.encode_command_long(
            mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,
            1,
            pitch, roll, yaw,
            0, 0, 0,
            mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING
        )

        self.mavlink_controller.send_packet(command)

    def set_roi_location(self, latitude, longitude, altitude):
        latitude_int = int(latitude * 10 ** 7)
        longitude_int = int(longitude * 10 ** 7)

        command = self.mavlink_controller.encode_command_int(
            mavutil.mavlink.MAV_FRAME_GLOBAL_INT,
            mavutil.mavlink.MAV_CMD_DO_SET_ROI_LOCATION,
            0, 0, 0, 0,
            latitude_int, longitude_int, altitude
        )

        self.mavlink_controller.send_packet(command)

    def disable_roi(self):
        command = self.mavlink_controller.encode_command_int(
            0,
            mavutil.mavlink.MAV_CMD_DO_SET_ROI_NONE,
            0, 0, 0, 0,
            0, 0, 0
        )

        self.mavlink_controller.send_packet(command)


class DataAcquisitionThread(threading.Thread):
    def __init__(self, mavlink_handler, processor_list, delay=1/100):
        super().__init__()
        self.mavlink_handler = mavlink_handler
        self.processor_list = processor_list
        self.delay = delay

    def find_interested(self, packet):
        for processor in self.processor_list:
            if packet.msgname == processor.data_type.value:
                processor.add_data(packet)

    def run(self):
        while True:
            packet = self.mavlink_handler.receive_data()

            self.find_interested(packet)

            time.sleep(self.delay)
