import math
from ultralytics import YOLO
from .deep_sort.deep_sort.tracker import Tracker
from .deep_sort.deep_sort.deep.extractor import Extractor
from .deep_sort.deep_sort.deep.configuration import ResNetConfiguration
from .deep_sort.deep_sort.deep.weights import RESNET18_WEIGHTS
from .geospatial import GEOSpatial


class DroneAnalysisService:
    def __init__(self, model_path, dem_path, classes=None, detection_threshold=0.3, iou_threshold=0.5, max_detections=10):
        self.model = YOLO(model_path)
        self.detection_threshold = detection_threshold
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections
        self.classes = classes

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

        self.geospatial = GEOSpatial(dem_path)

    def predict(self, frame):
        result = self.model.predict(
            source=frame,
            imgsz=frame.shape[:2],
            classes=self.classes,
            conf=self.detection_threshold,
            iou=self.iou_threshold,
            max_det=self.max_detections,
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

        return detections

    def update_tracker(self, frame, detections):
        self.tracker.update(frame, detections)

        return self.tracker.tracks

    def geospatial_analysis(self, tracks, image_width, image_height, fov_horizontal, fov_vertical, gimbal_data, attitude_data, global_position_data):
        gimbal_roll, gimbal_pitch, gimbal_yaw = gimbal_data.quaternion.to_euler()
        drone_roll = math.radians(attitude_data.roll)
        drone_pitch = math.radians(attitude_data.pitch)
        drone_heading = math.radians(global_position_data.heading)

        view_roll = gimbal_roll + drone_roll
        view_pitch = gimbal_pitch + drone_pitch
        view_yaw = gimbal_yaw + drone_heading

        tracks_locations = {}
        for track in tracks:
            x1, y1, x2, y2 = track.to_tlbr()
            track_id = track.track_id

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

            tracks_locations[track_id] = target_location

        return tracks_locations
