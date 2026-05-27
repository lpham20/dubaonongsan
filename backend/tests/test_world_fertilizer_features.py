from datetime import UTC, datetime, timedelta

import numpy as np

from app.ml_engine.world_fertilizer_features import (
    FEATURE_COLUMNS,
    build_inference_tensor,
    feature_scaler,
    normalize_commodity_slug,
    normalize_features,
    raw_feature_matrix,
)


def test_world_fertilizer_feature_pipeline_is_shared_for_train_and_runtime():
    points = [
        (datetime(2026, 5, 1, tzinfo=UTC) + timedelta(days=index), 500 + index * 3, "benchmark")
        for index in range(8)
    ]
    raw = raw_feature_matrix(points)
    feature_mean, feature_std = feature_scaler(raw)
    expected = normalize_features(raw, feature_mean, feature_std)

    tensor = build_inference_tensor(
        points,
        {
            "feature_mean": feature_mean.tolist(),
            "feature_std": feature_std.tolist(),
        },
    )

    assert raw.shape == (8, len(FEATURE_COLUMNS))
    assert tensor.shape == (1, 8, len(FEATURE_COLUMNS))
    assert np.allclose(tensor[0], expected)
    assert normalize_commodity_slug("Urea-Benchmark") == "urea_benchmark"
