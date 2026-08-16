"""
Inference service: the ONLY place in the application that performs ML
prediction. The routers, storage layer, and schemas must not depend on
any model-specific detail (architecture, weights, preprocessing, etc.).

This module is the single seam that the ML teammate will replace once the
final model file, preprocessing requirements, input dimensions, and class
mapping are provided.

The full pipeline (once the model is integrated) will be:

    private Supabase image
        ↓            (download bytes via app.services.storage.download_image)
    download bytes
        ↓            (load with Pillow in the calling endpoint)
    PIL Image
        ↓            (convert to RGB)
    RGB
        ↓            (ML preprocessing: resize / normalize — TBD)
    ML preprocessing
        ↓            (build input tensor — TBD)
    PyTorch tensor
        ↓            (run the CNN/model — TBD)
    CNN/model
        ↓
    numeric class
        ↓            (map via PREDICTION_LABELS)
    prediction label

None of the steps below the Pillow stage are implemented yet.
"""

from PIL import Image as PILImage


# Placeholder class mapping.
#
# The ML teammate may eventually provide a model that returns numeric
# classes such as 1, 2, 3, 4. Their meaning is NOT known yet, so the
# labels are left as "TODO" and must NOT be assumed.
PREDICTION_LABELS: dict[int, str] = {
    1: "TODO",
    2: "TODO",
    3: "TODO",
    4: "TODO",
}


class InferenceNotImplemented(NotImplementedError):
    """
    Raised when the ML model has not been integrated yet. The endpoint
    translates this into an HTTP 501 response.
    """


def predict_image(image: PILImage.Image) -> int:
    """
    Run the ML pipeline on a single Pillow image and return the predicted
    numeric class (an integer such as 1, 2, 3, 4).

    TODO(model integration) — replace this placeholder body:
    * Convert ``image`` to RGB.
    * Apply the ML preprocessing steps (input dimensions, normalization
      values) defined by the ML teammate.
    * Build the input tensor.
    * Load the model weights (path / loading mechanism defined by the ML
      teammate — not a .pkl assumption).
    * Run the forward pass and return the predicted class.
    """
    raise InferenceNotImplemented(
        "ML model inference is not implemented yet; "
        "the inference service will return a numeric class once the "
        "model is integrated."
    )


def label_for_class(code: int) -> str:
    """
    Map a numeric class code to its human-readable label using the
    PREDICTION_LABELS placeholder mapping.
    """
    return PREDICTION_LABELS[code]
