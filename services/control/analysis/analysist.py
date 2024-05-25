import math
from ultralytics import YOLO
from .deep_sort.deep_sort.tracker import Tracker
from .deep_sort.deep_sort.deep.extractor import Extractor
from .deep_sort.deep_sort.deep.configuration import ResNetConfiguration
from .deep_sort.deep_sort.deep.weights import RESNET18_WEIGHTS
from .geospatial import GEOSpatial


class DroneAnalysisService:
    def __init__(self, yolov8_model_path, geospatial_file_path):
        self.model = YOLO(yolov8_model_path)
        self.detection_threshold = 0.3

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

        self.geospatial = GEOSpatial(geospatial_file_path)

    def process_frame(self, camera_frame, image_width, image_height, fov_horizontal):
        fov_vertical = 2 * math.atan(math.tan(fov_horizontal / 2) * (image_height / image_width))

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

        self.tracker.update(camera_frame, detections)

        return detections, fov_vertical

    def analyze(self, camera_frame, image_width, image_height, fov_horizontal, gimbal_data, attitude_data,
                global_position_data):
        detections, fov_vertical = self.process_frame(camera_frame, image_width, image_height, fov_horizontal)

        gimbal_roll, gimbal_pitch, gimbal_yaw = gimbal_data.quaternion.to_euler()
        drone_roll = math.radians(attitude_data.roll)
        drone_pitch = math.radians(attitude_data.pitch)
        drone_heading = math.radians(global_position_data.heading)

        view_roll = gimbal_roll + drone_roll
        view_pitch = gimbal_pitch + drone_pitch
        view_yaw = gimbal_yaw + drone_heading

        target_locations = []
        for track in self.tracker.tracks:
            x1, y1, x2, y2 = track.to_tlbr()
            track_id = track.track_id
            class_id = track.class_id

            detection_offset = self.geospatial.detection_angles(
                self.geospatial.find_center(x1, y1, x2, y2),
                (image_width, image_height),
                fov_horizontal,
                fov_vertical
            )
            direction_vector = self.geospatial.calculate_direction_vector(
                (view_roll, view_pitch, view_yaw),
                detection_offset
            )
            target_location = self.geospatial.find_target_location(
                global_position_data,
                direction_vector
            )

            target_locations.append({
                "track_id": track_id,
                "class_id": class_id,
                "location": target_location
            })

        return target_locations


yolov8_model_path = "yolov8n-visdrone.pt"
geospatial_file_path = "S36E149.hgt"

if __name__ == "__main__":
    analysis_service = DroneAnalysisService(yolov8_model_path, geospatial_file_path)

    camera_frame = ...
    image_width = ...
    image_height = ...
    fov_horizontal = ...
    gimbal_data = ...
    attitude_data = ...
    global_position_data = ...

    target_locations = analysis_service.analyze(
        camera_frame,
        image_width,
        image_height,
        fov_horizontal,
        gimbal_data,
        attitude_data,
        global_position_data
    )
    print("Target Locations:", target_locations)
