from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings


CROPS = ("sau_rieng", "ca_phe", "ho_tieu", "lua")
DEFAULT_TARGET_MODE_BY_CROP = {
    "ca_phe": "price",
    "lua": "price",
}


def fix_lstm_target_modes(artifacts_dir: Path | None = None) -> list[dict]:
    base = artifacts_dir or Path(get_settings().ml_artifacts)
    results: list[dict] = []
    for crop in CROPS:
        meta_path = base / f"lstm_{crop}.meta.json"
        scaler_path = base / f"lstm_{crop}.scaler.json"
        tflite_meta_path = base / f"lstm_{crop}.tflite.meta.json"
        if not meta_path.exists() or not scaler_path.exists():
            results.append({"crop": crop, "status": "missing"})
            continue

        meta = _read_json(meta_path)
        scaler = _read_json(scaler_path)
        tflite_meta = _read_json(tflite_meta_path) if tflite_meta_path.exists() else {}
        target_mode = (
            scaler.get("target_mode")
            or meta.get("target_mode")
            or tflite_meta.get("target_mode")
            or DEFAULT_TARGET_MODE_BY_CROP.get(crop, "delta")
        )
        scaler["target_mode"] = target_mode
        meta["target_mode"] = target_mode
        if tflite_meta_path.exists():
            tflite_meta["target_mode"] = target_mode
            _write_json(tflite_meta_path, tflite_meta)
        _write_json(scaler_path, scaler)
        _write_json(meta_path, meta)
        results.append({"crop": crop, "status": "updated", "target_mode": target_mode})
    return results


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for item in fix_lstm_target_modes():
        print(json.dumps(item, ensure_ascii=False))
