from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import logging
from pathlib import Path
import threading
from typing import Any

from app.core.config import get_settings
from app.ml_engine.normalization import Scaler


logger = logging.getLogger(__name__)
_CACHE: OrderedDict[str, "TFLiteArtifact"] = OrderedDict()
_CACHE_LOCK = threading.Lock()


@dataclass
class TFLiteArtifact:
    crop_type: str
    interpreter: Any
    scaler: Scaler
    input_details: list[dict[str, Any]]
    output_details: list[dict[str, Any]]
    model_path: Path
    lock: threading.Lock
    model_kind: str = "lstm-tflite"


def load_lstm_artifact(crop_type: str) -> TFLiteArtifact | None:
    settings = get_settings()
    if not settings.ml_enable_tflite:
        return None

    key = _normalize_crop(crop_type)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return cached

    artifacts_dir = Path(settings.ml_artifacts)
    model_path = artifacts_dir / f"lstm_{key}.tflite"
    scaler_path = artifacts_dir / f"lstm_{key}.scaler.json"
    if not model_path.exists() or not scaler_path.exists():
        return None

    try:
        tflite = _load_tflite_module()
        interpreter = tflite.Interpreter(model_path=str(model_path))
        interpreter.allocate_tensors()
        scaler = Scaler.from_json(scaler_path.read_text(encoding="utf-8"))
        artifact = TFLiteArtifact(
            crop_type=key,
            interpreter=interpreter,
            scaler=scaler,
            input_details=interpreter.get_input_details(),
            output_details=interpreter.get_output_details(),
            model_path=model_path,
            lock=threading.Lock(),
        )
    except Exception as exc:
        logger.exception("Failed to load TFLite artifact crop=%s: %s", key, exc)
        return None

    with _CACHE_LOCK:
        _CACHE[key] = artifact
        _CACHE.move_to_end(key)
        max_models = max(1, int(settings.ml_max_models or 1))
        while len(_CACHE) > max_models:
            evicted_key, _ = _CACHE.popitem(last=False)
            logger.info("Evicted TFLite artifact from cache crop=%s", evicted_key)

    logger.info("Loaded TFLite artifact crop=%s path=%s size_kb=%d", key, model_path, model_path.stat().st_size // 1024)
    return artifact


def invalidate_model_cache(crop_type: str | None = None) -> None:
    with _CACHE_LOCK:
        if crop_type is None:
            _CACHE.clear()
        else:
            _CACHE.pop(_normalize_crop(crop_type), None)


def _load_tflite_module():
    try:
        import tflite_runtime.interpreter as tflite

        return tflite
    except ImportError:
        pass

    try:
        from tensorflow import lite as tflite

        return tflite
    except ImportError as exc:
        raise RuntimeError("No TFLite interpreter installed") from exc


def _normalize_crop(crop_type: str) -> str:
    return crop_type.strip().lower().replace("-", "_")
