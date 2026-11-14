"""Facial biometrics infrastructure (ADR 0008).

Only the numeric template is kept, encrypted with a key that lives outside the database.
Images are processed in memory and discarded in the same request; they never reach logs,
events, audit records or error messages. The engine is isolated behind ``FaceEngine`` so
the installation can replace it (for example by a certified commercial SDK).
"""

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}


class FaceEngineUnavailable(Exception):
    """The installation has no usable engine or key; the counter uses the signed term."""


class FaceEngine(Protocol):
    version: str
    threshold: float

    def template(self, image: bytes) -> bytes:
        """Return the template of the single face in the image or raise ValidationError."""

    def similarity(self, first: bytes, second: bytes) -> float:
        """Return the similarity between two templates of the same engine version."""


@dataclass(frozen=True)
class Comparison:
    approved: bool
    engine_version: str


def engine() -> FaceEngine:
    path = settings.SIGAB_FACE_ENGINE
    if not path:
        raise FaceEngineUnavailable("Verificação facial não configurada nesta instalação.")
    try:
        return import_string(path)()
    except FaceEngineUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - never leak engine internals to the client
        raise FaceEngineUnavailable("Motor de verificação facial indisponível.") from exc


def _fernet():
    key = settings.SIGAB_BIOMETRIC_KEY
    if not key:
        raise FaceEngineUnavailable("Chave de proteção biométrica não configurada.")
    from cryptography.fernet import Fernet

    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise FaceEngineUnavailable("Chave de proteção biométrica inválida.") from exc


def encrypt(template: bytes) -> bytes:
    return _fernet().encrypt(template)


def decrypt(token: bytes) -> bytes:
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(bytes(token))
    except InvalidToken as exc:
        raise FaceEngineUnavailable("Modelo biométrico ilegível com a chave atual.") from exc


def read_image(upload) -> bytes:
    """Validate an uploaded capture without persisting it."""
    if upload is None:
        raise ValidationError({"image": "Envie a captura do rosto."})
    if upload.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError({"image": "Use imagem JPEG ou PNG."})
    if upload.size > settings.SIGAB_FACE_MAX_IMAGE_BYTES:
        raise ValidationError({"image": "A imagem excede o tamanho permitido."})
    return upload.read()


def compare(face_engine: FaceEngine, stored: bytes, image: bytes) -> Comparison:
    probe = face_engine.template(image)
    score = face_engine.similarity(decrypt(stored), probe)
    # The raw score is deliberately not returned nor recorded (ADR 0008, section 9).
    return Comparison(approved=score >= face_engine.threshold, engine_version=face_engine.version)


class OpenCVFaceEngine:
    """OpenCV YuNet (detection) + SFace (recognition), Apache 2.0 models.

    Requires the optional dependency group ``face`` and the model files configured in
    SIGAB_FACE_DETECTOR_MODEL and SIGAB_FACE_RECOGNIZER_MODEL. It performs no certified
    liveness detection: the operator's visual confirmation is mandatory (ADR 0008, sec. 3).
    """

    version = "opencv-yunet-sface-2021dec"

    def __init__(self):
        try:
            import cv2
            import numpy
        except ImportError as exc:
            raise FaceEngineUnavailable("Dependências do motor facial não instaladas.") from exc
        if not settings.SIGAB_FACE_DETECTOR_MODEL or not settings.SIGAB_FACE_RECOGNIZER_MODEL:
            raise FaceEngineUnavailable("Modelos do motor facial não configurados.")
        self._cv2, self._np = cv2, numpy
        self.threshold = settings.SIGAB_FACE_THRESHOLD
        self._detector = cv2.FaceDetectorYN.create(
            settings.SIGAB_FACE_DETECTOR_MODEL, "", (320, 320), 0.9, 0.3, 5000
        )
        self._recognizer = cv2.FaceRecognizerSF.create(settings.SIGAB_FACE_RECOGNIZER_MODEL, "")

    def template(self, image: bytes) -> bytes:
        cv2, np = self._cv2, self._np
        frame = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValidationError({"image": "Imagem ilegível."})
        height, width = frame.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(frame)
        if faces is None or len(faces) == 0:
            raise ValidationError(
                {"image": "Nenhum rosto encontrado. Centralize o rosto e repita."}
            )
        if len(faces) > 1:
            raise ValidationError({"image": "Mais de um rosto na imagem. Capture apenas a pessoa."})
        aligned = self._recognizer.alignCrop(frame, faces[0])
        feature = self._recognizer.feature(aligned)
        return np.asarray(feature, dtype=np.float32).tobytes()

    def similarity(self, first: bytes, second: bytes) -> float:
        np = self._np
        a = np.frombuffer(first, dtype=np.float32).reshape(1, -1)
        b = np.frombuffer(second, dtype=np.float32).reshape(1, -1)
        return float(self._recognizer.match(a, b, self._cv2.FaceRecognizerSF_FR_COSINE))
