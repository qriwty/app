from communication.communicator import DroneDataService
from analysis.analysist import DroneAnalysisService


class DroneCoreService:
    def __init__(self, mavlink_address, stream_host, stream_port, yolov8_model_path, geospatial_file_path):
        self.data_service = DroneDataService(mavlink_address, stream_host, stream_port)
        self.analysis_service = DroneAnalysisService(yolov8_model_path, geospatial_file_path)

    def get_data(self):
        mavlink_data = self.data_service.get_mavlink_data()
        drone_data = self.data_service.get_drone_data()
        return mavlink_data, drone_data

    def process_data(self, mavlink_data, drone_data):
        camera_frame = drone_data.camera.frame
        image_width = drone_data.camera.width
        image_height = drone_data.camera.height
        fov_horizontal = drone_data.camera.fov
        gimbal_data = mavlink_data["gimbal"]
        attitude_data = mavlink_data["attitude"]
        global_position_data = mavlink_data["position"]

        target_locations = self.analysis_service.analyze(
            camera_frame,
            image_width,
            image_height,
            fov_horizontal,
            gimbal_data,
            attitude_data,
            global_position_data
        )

        return target_locations

    def run_analysis(self):
        mavlink_data, drone_data = self.get_data()

        all_data = {
            "mavlink_data": mavlink_data,
            "drone_data": drone_data
        }

        target_locations = self.process_data(mavlink_data, drone_data)

        return all_data, target_locations


if __name__ == "__main__":
    mavlink_address = "udp:0.0.0.0:14550"
    stream_host = "192.168.0.107"
    stream_port = 5588
    yolov8_model_path = "analysis/yolov8n-visdrone.pt"
    geospatial_file_path = "analysis/S36E149.hgt"

    core_service = DroneCoreService(mavlink_address, stream_host, stream_port, yolov8_model_path, geospatial_file_path)

    all_data, target_locations = core_service.run_analysis()

    print("All Drone Data:", all_data)

    print("Target Locations:", target_locations)
