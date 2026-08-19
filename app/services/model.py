"""
CNN model definition and weight loading for pneumonia detection.

The architecture mirrors the model trained in ``cnn.py``: three conv
blocks (32/64/128 channels, 3x3 kernels, ReLU, 2x2 max-pool) followed by
a 2-class classifier. It expects 224x224 RGB inputs normalized with
ImageNet statistics (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]).

The trained weights live in a state_dict saved with ``torch.save``; this
module is the only place that knows about the model file and its format.
"""

import logging
from pathlib import Path

import torch
import torch.nn as nn

from app.config import settings

logger = logging.getLogger(__name__)

MODEL_VERSION = "cnn-v1"


class PneumoniaCNN(nn.Module):
    """
    Binary classifier trained on the Kaggle chest X-ray (pneumonia)
    dataset. Outputs logits for 2 classes: 0 = NORMAL, 1 = PNEUMONIA.
    """

    def __init__(self) -> None:
        super().__init__()

        self.features = nn.Sequential(
            # Convolution 1
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            # Convolution 2
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            # Convolution 3
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 28 * 28, 128),
            nn.ReLU(),
            nn.Linear(128, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        return self.classifier(x)


_model: PneumoniaCNN | None = None
_device: torch.device | None = None


def get_device() -> torch.device:
    """Return the preferred torch device, cached after the first call."""
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def load_model() -> PneumoniaCNN:
    """
    Load the trained weights into the CNN once per process and return the
    model in evaluation mode. Raises FileNotFoundError when MODEL_PATH does
    not point at a weights file.
    """
    global _model
    if _model is None:
        model_path = Path(settings.MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model weights not found at {model_path}. "
                "Set MODEL_PATH to the location of the trained .pth file."
            )
        device = get_device()
        model = PneumoniaCNN().to(device)
        state_dict = torch.load(model_path, map_location=device, weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()
        _model = model
        logger.info("Loaded pneumonia model from %s on %s", model_path, device)
    return _model
