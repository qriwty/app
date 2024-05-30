import os
import torch


class FeatureModel:
    def __init__(self, use_cuda=False):
        self.device = torch.device("cuda" if use_cuda and torch.cuda.is_available() else "cpu")
        self.model_base = None
        self.weights_path = None
        self.input_shape = None
        self.feature_layer = None
        self._preprocessor = None

    def load(self, weights_path):
        if os.path.exists(weights_path):
            self.model_base.load_state_dict(torch.load(weights_path, map_location=self.device))
            print(f"Model weights loaded from {weights_path}")
        else:
            print(f"No weights file found at {weights_path}, using default pretrained weights.")

    def save(self, weights_path):
        torch.save(self.model_base.state_dict(), weights_path)

    def preprocess(self, image):
        if self._preprocessor is not None:
            return self._preprocessor(image)
        else:
            raise NotImplementedError("Preprocessor must be defined in the subclass.")
