from .feature_model import FeatureModel

import torch
from torchvision import transforms
from torchvision.models import (
    resnet18, ResNet18_Weights,
    resnet34, ResNet34_Weights,
    resnet50, ResNet50_Weights
)


class ResNetConfiguration(FeatureModel):
    def __init__(self, base="resnet18", weights_path=None, use_cuda=False):
        super(ResNetConfiguration, self).__init__(use_cuda=use_cuda)

        self._models = {
            "resnet18": {
                "model": resnet18,
                "weights": ResNet18_Weights
            },
            "resnet34": {
                "model": resnet34,
                "weights": ResNet34_Weights
            },
            "resnet50": {
                "model": resnet50,
                "weights": ResNet50_Weights
            }
        }

        self.weights_path = weights_path

        self.model_base = self._get_model_base(base)
        self.model_base.to(self.device)

        self.input_shape = (224, 224)

        self.feature_layer = "avgpool"

        self._preprocessor = transforms.Compose([
            transforms.Resize(self.input_shape),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def _get_model_base(self, base):
        if base not in self._models:
            raise ValueError(f"Model {base} is not supported. Choose from {list(self._models.keys())}.")

        if self.weights_path:
            model_base = self._models[base]["model"](weights=None)
            model_base.load_state_dict(torch.load(self.weights_path))
        else:
            model_weights = self._models[base]["weights"]
            model_base = self._models[base]["model"](weights=model_weights)

        return model_base
