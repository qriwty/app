from .mavlink.mavlink import MAVLinkController, DataAcquisitionThread
from .mavlink.mavlink.processor import GimbalProcessor, GlobalPositionProcessor, AttitudeProcessor
from .data_stream import StreamReceiver
from .drone_data import DroneData


class DroneDataService:
    def __init__(self, mavlink_connection_str, host, port):
        self.mavlink_connection = MAVLinkController(mavlink_connection_str)

        self.attitude_processor = AttitudeProcessor()
        self.global_position_processor = GlobalPositionProcessor()
        self.gimbal_processor = GimbalProcessor()

        self.acquisition_thread = DataAcquisitionThread(
            self.mavlink_connection,
            [
                self.attitude_processor,
                self.global_position_processor,
                self.gimbal_processor
            ]
        )
        self.acquisition_thread.start()

        self.stream_receiver = StreamReceiver(host, port)

    def get_mavlink_data(self):
        attitude_data = self.attitude_processor.get_data()
        position_data = self.global_position_processor.get_data()
        gimbal_data = self.gimbal_processor.get_data()

        return {
            "attitude": attitude_data,
            "position": position_data,
            "gimbal": gimbal_data
        }

    def get_drone_data(self):
        data = self.stream_receiver.get_data()
        drone_data = DroneData.from_json(data)

        return drone_data


if __name__ == "__main__":
    mavlink_address = "udp:0.0.0.0:14550"
    stream_host = "192.168.0.107"
    stream_port = 5588

    service = DroneDataService(mavlink_address, stream_host, stream_port)

    mavlink_data = service.get_mavlink_data()
    print("MAVLink Data:", mavlink_data)

    drone_data = service.get_drone_data()
    print("Drone Data:", drone_data)


