import math
from ultralytics import YOLO
from deep_sort.deep_sort.tracker import Tracker
from deep_sort.deep_sort.deep.extractor import Extractor
from deep_sort.deep_sort.deep.configuration import ResNetConfiguration
from deep_sort.deep_sort.deep.weights import RESNET18_WEIGHTS
import geospatial as geo_utils
from data_stream import StreamReceiver
from simulation.webots.controllers.ardupilot_vehicle_controller.drone_data import DroneData
from mavlink.mavlink.processor import GimbalProcessor, GlobalPositionProcessor, AttitudeProcessor


class DroneAnalysisService:
    def __init__(self, yolov8_model_path, geospatial_file_path, stream_host, stream_port, mavlink_address):
        # Initialize YOLO model
        self.model = YOLO(yolov8_model_path)
        self.detection_threshold = 0.3

        # Initialize DeepSORT tracker
        resnet = ResNetConfiguration(
            base="resnet18",
            weights_path=RESNET18_WEIGHTS,
            use_cuda=False
        )
        self.extractor = Extractor(model=resnet, batch_size=4)
        self.tracker = Tracker(
            feature_extractor=self.extractor,
            max_iou_distance=0.7,
            max_cosine_distance=0.7
        )

        # Initialize GEOSpatial
        self.geospatial = geo_utils.GEOSpatial(geospatial_file_path)

        # Initialize stream receiver
        self.stream_receiver = StreamReceiver(stream_host, stream_port)

        # Initialize MAVLink processors
        self.gimbal_processor = GimbalProcessor()
        self.global_position_processor = GlobalPositionProcessor()
        self.attitude_processor = AttitudeProcessor()

    def process_frame(self, camera_frame, image_width, image_height, fov_horizontal):
        fov_vertical = 2 * math.atan(math.tan(fov_horizontal / 2) * (image_height / image_width))

        # Object detection
        result = self.model.predict(
            source=camera_frame,
            imgsz=camera_frame.shape[:2],
            classes=None,
            conf=self.detection_threshold,
            iou=0.5,
            max_det=10,
            augment=False,
            agnostic_nms=True,
            device="cpu",
            half=False,
            verbose=False
        )[0]

        detections = []
        for res in result.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = res
            x1, x2, y1, y2 = map(int, (x1, x2, y1, y2))
            class_id = int(class_id)
            detections.append([x1, y1, x2, y2, score, class_id])

        # Update tracker
        self.tracker.update(camera_frame, detections)

        return detections, fov_vertical

    def analyze(self):
        # Retrieve data from stream receiver
        data = self.stream_receiver.get_data()
        drone_data = DroneData.from_json(data)
        camera_frame = drone_data.camera.frame

        image_width = drone_data.camera.width
        image_height = drone_data.camera.height
        fov_horizontal = drone_data.camera.fov

        # Process frame and get detections
        detections, fov_vertical = self.process_frame(camera_frame, image_width, image_height, fov_horizontal)

        # Get MAVLink data
        gimbal_roll, gimbal_pitch, gimbal_yaw = self.gimbal_processor.get_data().quaternion.to_euler()
        attitude = self.attitude_processor.get_data()
        drone_roll = math.radians(attitude.roll)
        drone_pitch = math.radians(attitude.pitch)

        global_position = self.global_position_processor.get_data()
        drone_heading = math.radians(global_position.heading)

        view_roll = gimbal_roll + drone_roll
        view_pitch = gimbal_pitch + drone_pitch
        view_yaw = gimbal_yaw + drone_heading

        # Analyze tracks and calculate target locations
        target_locations = []
        for track in self.tracker.tracks:
            x1, y1, x2, y2 = track.to_tlbr()
            track_id = track.track_id
            class_id = track.class_id

            detection_offset = geo_utils.detection_angles(geo_utils.find_center(x1, y1, x2, y2),
                                                          (image_width, image_height), fov_horizontal, fov_vertical)
            direction_vector = geo_utils.calculate_direction_vector((view_roll, view_pitch, view_yaw), detection_offset)
            target_location = geo_utils.find_target_location(global_position, direction_vector, self.geospatial)

            target_locations.append({
                "track_id": track_id,
                "class_id": class_id,
                "location": target_location
            })

        return target_locations


# Example usage:
yolov8_model_path = "yolov8n-visdrone.pt"
geospatial_file_path = "S36E149.hgt"
stream_host = "192.168.0.107"
stream_port = 5588
mavlink_address = "udp:0.0.0.0:14550"

analysis_service = DroneAnalysisService(yolov8_model_path, geospatial_file_path, stream_host, stream_port,
                                        mavlink_address)

# Perform analysis
target_locations = analysis_service.analyze()
print("Target Locations:", target_locations)
