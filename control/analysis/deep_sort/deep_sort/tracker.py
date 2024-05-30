import numpy as np

from .sort import nn_matching
from .sort.preprocessing import non_max_suppression
from .sort.tracker import Tracker as Sort
from .sort.detection import Detection
from .deep.extractor import Extractor

from .deep.configuration import ResNetConfiguration
from .deep.weights import RESNET18_WEIGHTS


class Tracker:
    def __init__(
        self,
        n_init=3,
        nn_budget=None,
        max_iou_distance=0.2,
        max_cosine_distance=0.2,
        max_age=100,
        feature_extractor=None,
        max_nms=1.0,
        use_cuda=True,
        batch_size=4
    ):
        self.max_nms = max_nms

        self.metric = nn_matching.NearestNeighborDistanceMetric(
            "cosine", max_cosine_distance, nn_budget
        )

        self.tracker = Sort(
            metric=self.metric,
            n_init=n_init,
            max_iou_distance=max_iou_distance,
            max_age=max_age
        )

        self.extractor = feature_extractor

        if self.extractor is None:
            resnet = ResNetConfiguration(weights_path=RESNET18_WEIGHTS, use_cuda=use_cuda)
            self.extractor = Extractor(model=resnet, batch_size=batch_size)

        self.tracks = None

    def update(self, frame, detections):
        if len(detections) == 0:
            self.tracker.predict()
            self.tracker.update([])

            self.update_tracks()

            return

        bboxes = np.asarray([d[:-2] for d in detections])
        bboxes[:, 2:] = bboxes[:, 2:] - bboxes[:, 0:2]
        scores = [d[-2] for d in detections]
        classes = [d[-1] for d in detections]

        indices = non_max_suppression(bboxes, self.max_nms, scores)

        features = self.extractor(frame, bboxes)

        dets = []
        for idx in indices:
            dets.append(Detection(bboxes[idx], scores[idx], features[idx], classes[idx]))

        self.tracker.predict()
        self.tracker.update(dets)

        self.update_tracks()

    def update_tracks(self):
        tracks = []
        for track in self.tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue

            tracks.append(track)

        self.tracks = tracks
