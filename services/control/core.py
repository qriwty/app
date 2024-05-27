import math
import threading

from sqlalchemy import desc

from .communication.communicator import DroneDataService
from .analysis.analysist import DroneAnalysisService

import cv2
from datetime import datetime
from app import db
from models.setting import Setting
from models.task import Task
from models.image import Image
from models.point import Point
from models.detection import Detection
from models.object import Object


class DroneCoreService:
    def __init__(self, mavlink_address, stream_host, stream_port, model_path, dem_path):
        self.data_service = DroneDataService(mavlink_address, stream_host, stream_port)
        self.analysis_service = DroneAnalysisService(
            model_path,
            dem_path
        )

        self.latest = None

    def execute_command(self, command):
        command_parts = command.split()

        command_target = command_parts[0]
        command_name = command_parts[1]
        command_module = command_parts[2]
        command_args = command_parts[3:]

        if command_target == "GIMBAL":
            if command_name == "SET_ANGLES":
                roll, pitch, yaw = map(float, command_args)

                self.data_service.mavlink_connection.gimbal.set_angles(
                    roll, pitch, yaw
                )

                return roll, pitch, yaw

            elif command_name == "SET_ROI":
                if command_module == "ANALYSIS":
                    object_id = command_args
                    latest_detection = db.session.query(Detection) \
                        .filter_by(object_id=object_id) \
                        .order_by(desc(Detection.created)) \
                        .first()

                    if not latest_detection:
                        return None

                    point = db.session.query(Point).get(latest_detection.point_id)

                    if not point:
                        return None

                    self.data_service.mavlink_connection.gimbal.set_roi_location(
                        point.latitude,
                        point.longitude,
                        point.altitude
                    )

                    return point

                latitude, longitude, altitude = map(float, command_args)

                self.data_service.mavlink_connection.gimbal.set_roi_location(
                    latitude, longitude, altitude
                )

                return latitude, longitude, altitude

            elif command_name == "DISABLE_ROI":
                self.data_service.mavlink_connection.gimbal.disable_roi()

                return 0

        elif command_target == "DRONE":
            if command_name == "ARM":
                # packet = self.data_service.mavlink_connection.encode_command_long(
                #     400,
                #     1,
                #     0, 0, 0, 0, 0, 0, 0
                # )
                #
                # self.data_service.mavlink_connection.send_packet(packet)
                #
                # return self.data_service.mavlink_connection.connection.recv_match(
                #     type='COMMAND_ACK', blocking=True, timeout=3
                # )
                pass

            elif command_name == "DISARM":
                pass

            elif command_name == "TAKEOFF":
                pass

    def update_settings(self, flight_id):
        settings = db.session.query(Setting).filter_by(flight_id=flight_id).all()
        settings_dict = {setting.parameter: setting.value for setting in settings}

        detection_threshold = float(settings_dict.get('confidence', 0.5))
        iou_threshold = float(settings_dict.get('jaccard_index', 0.5))
        max_detections = int(settings_dict.get('detection_limit', 100))
        classes_excluded = list(map(int, settings_dict.get('exclude_classes', '-1').split(',')))

        self.analysis_service.detection_threshold = detection_threshold
        self.analysis_service.iou_threshold = iou_threshold
        self.analysis_service.max_detections = max_detections
        self.analysis_service.classes = [key for key in self.analysis_service.model.names.keys() if key not in classes_excluded]

    def get_drone_data(self):
        drone_data = self.data_service.get_drone_data()

        camera_frame = drone_data.camera.frame
        image_width = drone_data.camera.width
        image_height = drone_data.camera.height
        fov_horizontal = drone_data.camera.fov
        fov_vertical = 2 * math.atan(math.tan(fov_horizontal / 2) * (image_height / image_width))

        return camera_frame, image_width, image_height, fov_horizontal, fov_vertical

    def get_mavlink_data(self):
        mavlink_data = self.data_service.get_mavlink_data()

        gimbal_data = mavlink_data["gimbal"]
        attitude_data = mavlink_data["attitude"]
        global_position_data = mavlink_data["position"]

        return gimbal_data, attitude_data, global_position_data

    def run_analysis(self, flight_id):
        self.update_settings(flight_id)

        camera_frame, image_width, image_height, fov_horizontal, fov_vertical = self.get_drone_data()
        gimbal_data, attitude_data, global_position_data = self.get_mavlink_data()

        image_object = self.save_image(flight_id, camera_frame)

        detections = self.analysis_service.predict(camera_frame)

        tracks = self.analysis_service.update_tracker(camera_frame, detections)

        tracks_locations = self.analysis_service.geospatial_analysis(
            tracks,
            image_width, image_height,
            fov_horizontal, fov_vertical,
            gimbal_data, attitude_data, global_position_data
        )

        for track in tracks:
            x1, y1, x2, y2 = track.to_tlbr()
            track_id = track.track_id
            class_id = track.class_id

            location = tracks_locations[track_id]

            track_object = self.save_object(track_id)

            point = self.save_point(*location)

            detection = self.save_detection(
                point.id,
                image_object.id,
                track_id,
                class_id,
                f"{[int(value) for value in (x1, y1, x2, y2)]}"
            )

        self.latest = [image_object]

    def save_image(self, flight_id, image_data):
        _, compressed_image = cv2.imencode('.jpg', image_data, [cv2.IMWRITE_JPEG_QUALITY, 70])
        image_bytes = compressed_image.tobytes()

        new_image = Image(
            flight_id=flight_id,
            timestamp=datetime.now(),
            image=image_bytes
        )

        db.session.add(new_image)
        db.session.commit()

        return new_image

    def save_detection(self, point_id, image_id, object_id, class_name, frame):
        new_detection = Detection(
            point_id=point_id,
            image_id=image_id,
            object_id=object_id,
            class_name=class_name,
            frame=frame
        )

        db.session.add(new_detection)
        db.session.commit()

        return new_detection

    def save_point(self, latitude, longitude, altitude):
        new_point = Point(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude
        )

        db.session.add(new_point)
        db.session.commit()

        return new_point

    def save_object(self, object_id):
        existing_object = Object.query.get(object_id)

        if existing_object:
            return existing_object

        new_object = Object(id=object_id)

        db.session.add(new_object)
        db.session.commit()

        return new_object
