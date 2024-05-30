import cv2
import torch
from PIL import Image

from torchvision.models.feature_extraction import create_feature_extractor


class Extractor(object):
    def __init__(self, model, batch_size=4):
        self.model = model
        self.batch_size = batch_size

        self.extractor = self.create_extractor()

    def create_extractor(self):
        return create_feature_extractor(self.model.model_base, return_nodes={self.model.feature_layer: self.model.feature_layer})

    def prepare_patches(self, frame, boxes):
        patches = []

        for box in boxes:
            x, y, w, h = box

            patch = frame[int(y):int(y + h), int(x):int(x + w)]
            patch = cv2.resize(patch, self.model.input_shape)

            image_patch = Image.fromarray(patch)

            patches.append(image_patch)

        return patches

    def create_batches(self, patches):
        batches = (len(patches) + self.batch_size - 1) // self.batch_size

        for i in range(batches):
            yield patches[i * self.batch_size:(i + 1) * self.batch_size]

    def extract_features(self, tensor):
        return self.extractor(tensor)[self.model.feature_layer]

    def __call__(self, frame, boxes):
        patches = self.prepare_patches(frame, boxes)

        batches = self.create_batches(patches)

        features = []
        for batch in batches:
            batch_tensor = torch.stack([self.model.preprocess(image) for image in batch])
            batch_tensor = batch_tensor.to(self.model.device)

            with torch.no_grad():
                batch_features = self.extract_features(batch_tensor)
                batch_features = batch_features.squeeze(-1).squeeze(-1)

            features.append(batch_features)

        features = torch.cat(features, dim=0)
        features = features.cpu()

        return features
