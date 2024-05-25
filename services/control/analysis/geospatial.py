import math
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform


class GEOSpatial:
    def __init__(self, file_path):
        self.file_path = file_path
        self.src = rasterio.open(self.file_path)
        self.resolution = self._estimate_resolution()

        self.elevation_cache = {}

    def _estimate_resolution(self):
        latitude_resolution = (self.src.bounds.top - self.src.bounds.bottom) / self.src.height
        longitude_resolution = (self.src.bounds.right - self.src.bounds.left) / self.src.width

        return max(latitude_resolution, longitude_resolution)

    def round_location(self, latitude, longitude):
        decimal_places = -int(math.floor(math.log10(self.resolution)))

        latitude_round = round(round(latitude / self.resolution) * self.resolution, decimal_places)
        longitude_round = round(round(longitude / self.resolution) * self.resolution, decimal_places)

        return latitude_round, longitude_round

    def find_elevation(self, latitude, longitude):
        latitude_key, longitude_key = self.round_location(latitude, longitude)

        if (latitude_key, longitude_key) in self.elevation_cache:
            return self.elevation_cache[(latitude_key, longitude_key)]

        transformed_point = transform(
            {"init": "epsg:4326"},
            self.src.crs,
            [longitude], [latitude]
        )

        row, col = self.src.index(transformed_point[0][0], transformed_point[1][0])

        elevation = self.src.read(
            1,
            window=rasterio.windows.Window(col, row, 1, 1),
            resampling=Resampling.nearest
        )

        elevation_value = elevation[0][0]

        self.elevation_cache[(latitude_key, longitude_key)] = elevation_value

        return elevation_value


def detection_angles(target_location, image_size, fov_horizontal, fov_vertical):
    x, y = target_location
    width, height = image_size
    theta_x = (x - width / 2) * fov_horizontal / width
    theta_y = -(y - height / 2) * fov_vertical / height

    return theta_x, theta_y


def find_center(x1, y1, x2, y2):
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    return center_x, center_y


def calculate_direction_vector(view_angles, detection_offset):
    view_roll, view_pitch, view_yaw = view_angles
    theta_x, theta_y = detection_offset

    final_roll = view_roll
    final_pitch = view_pitch + theta_y
    final_yaw = view_yaw + theta_x

    direction_vector = numpy.array([
        math.cos(final_pitch) * math.sin(final_yaw),
        math.cos(final_pitch) * math.cos(final_yaw),
        math.sin(final_pitch)
    ])

    cos_roll = math.cos(final_roll)
    sin_roll = math.sin(final_roll)
    rotation_matrix = numpy.array([
        [1, 0, 0],
        [0, cos_roll, -sin_roll],
        [0, sin_roll, cos_roll]
    ])
    direction_vector = numpy.dot(rotation_matrix, direction_vector)

    return direction_vector


def find_target_location(drone_position, direction_vector, geospatial):
    step_size = 0.1
    max_distance = 1000

    lat_step = step_size / 111320
    lon_step = step_size / (111320 * math.cos(math.radians(drone_position.latitude)))

    for i in range(1, int(max_distance / step_size)):
        d_lat = direction_vector[1] * lat_step * i
        d_lon = direction_vector[0] * lon_step * i
        d_alt = direction_vector[2] * step_size * i

        new_lat = drone_position.latitude + d_lat
        new_lon = drone_position.longitude + d_lon
        new_alt = drone_position.altitude + d_alt

        terrain_height = geospatial.find_elevation(new_lat, new_lon)

        if new_alt <= terrain_height:
            return new_lat, new_lon, terrain_height

    return None


def distance_between_locations(lat1, lon1, alt1, lat2, lon2, alt2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    lambda1, lambda2 = math.radians(lon1), math.radians(lon2)

    delta_phi = phi2 - phi1
    delta_lambda = lambda2 - lambda1
    delta_alt = alt2 - alt1

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    earth_radius = 6371000
    distance = earth_radius * c

    total_distance = math.sqrt(distance ** 2 + delta_alt ** 2)

    return total_distance
