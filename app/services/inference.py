"""
Inference service: the ONLY place in the application that performs ML
prediction. The routers, storage layer, and schemas do not depend on any
model-specific detail (architecture, weights, preprocessing, etc.).

The pipeline is:

    private Supabase image
        ↓            (download bytes via app.services.storage.download_image)
    download bytes
        ↓            (load with Pillow in the calling endpoint)
    PIL Image
        ↓            (convert to RGB)
    RGB
        ↓            (ML preprocessing: resize to 224x224 + ImageNet normalize)
    ML preprocessing
        ↓            (build input tensor)
    PyTorch tensor
        ↓            (run the CNN — see app.services.model)
    CNN
        ↓
    numeric class + softmax confidence
        ↓            (map via PREDICTION_LABELS)
    prediction label

The preprocessing and class mapping match the training script (cnn.py):
the Kaggle chest X-ray dataset is loaded with ``ImageFolder``, whose
classes are alphabetical, so 0 = NORMAL and 1 = PNEUMONIA.
"""

import logging

import torch
from PIL import Image as PILImage
from torchvision import transforms

from app.services.model import MODEL_VERSION, load_model

logger = logging.getLogger(__name__)


class InferenceNotImplemented(Exception):
    """Raised when the inference pipeline cannot run (e.g. model weights missing)."""

# Class order matches datasets.ImageFolder over the Kaggle chest_xray
# dataset (alphabetical): 0 = NORMAL, 1 = PNEUMONIA.
PREDICTION_LABELS: dict[int, str] = {
    0: "NORMAL",
    1: "PNEUMONIA",
}

# Preprocessing identical to the validation/test transform used in cnn.py.
_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def predict_image(image: PILImage.Image) -> tuple[int, float]:
    """
    Run the ML pipeline on a single Pillow image.

    Returns a ``(prediction_code, confidence)`` tuple where
    ``prediction_code`` is 0 (NORMAL) or 1 (PNEUMONIA) and ``confidence``
    is the softmax probability of the predicted class.
    """
    model = load_model()
    device = next(model.parameters()).device

    rgb = image.convert("RGB")
    tensor = _TRANSFORM(rgb).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)

    confidence, prediction_code = probs.max(dim=1)
    return int(prediction_code.item()), float(confidence.item())


def label_for_class(code: int) -> str:
    """
    Map a numeric class code to its human-readable label using the
    PREDICTION_LABELS mapping.
    """
    return PREDICTION_LABELS[code]
