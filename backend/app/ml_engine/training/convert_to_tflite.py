from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import tensorflow as tf


logger = logging.getLogger("marketai.convert_tflite")


def convert(crop_type: str, artifacts_dir: Path, quantize: bool = True) -> dict:
    keras_path = artifacts_dir / f"lstm_{crop_type}.keras"
    tflite_path = artifacts_dir / f"lstm_{crop_type}.tflite"
    meta_path = artifacts_dir / f"lstm_{crop_type}.tflite.meta.json"
    if not keras_path.exists():
        raise FileNotFoundError(keras_path)

    model = tf.keras.models.load_model(keras_path, compile=False)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    if quantize:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_bytes = converter.convert()

    tmp_path = tflite_path.with_suffix(".tflite.tmp")
    tmp_path.write_bytes(tflite_bytes)
    _verify_interpreter(tmp_path)
    tmp_path.replace(tflite_path)

    meta = {
        "crop_type": crop_type,
        "model_kind": "lstm-tflite",
        "quantized": quantize,
        "keras_size_kb": round(keras_path.stat().st_size / 1024, 2),
        "tflite_size_kb": round(tflite_path.stat().st_size / 1024, 2),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Converted %s: %s", crop_type, meta)
    return meta


def _verify_interpreter(path: Path) -> None:
    interpreter = tf.lite.Interpreter(model_path=str(path))
    interpreter.allocate_tensors()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", required=True)
    parser.add_argument("--artifacts-dir", default=Path("ml_artifacts"), type=Path)
    parser.add_argument("--no-quantize", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(convert(args.crop, args.artifacts_dir, quantize=not args.no_quantize), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
