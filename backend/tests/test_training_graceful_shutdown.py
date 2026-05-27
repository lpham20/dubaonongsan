from __future__ import annotations

import logging

import pytest

from app.ml_engine.training.graceful_shutdown import GracefulStopCallback, GracefulTrainingShutdown


def test_training_shutdown_first_signal_requests_graceful_stop() -> None:
    shutdown = GracefulTrainingShutdown(logging.getLogger("test"))

    shutdown._handle_signal(15, None)

    assert shutdown.stop_requested is True
    assert shutdown.signal_name == "SIGTERM"


def test_training_shutdown_second_signal_aborts_immediately() -> None:
    shutdown = GracefulTrainingShutdown(logging.getLogger("test"))
    shutdown._handle_signal(15, None)

    with pytest.raises(KeyboardInterrupt):
        shutdown._handle_signal(15, None)


def test_graceful_stop_callback_stops_after_current_epoch() -> None:
    class DummyModel:
        stop_training = False

    shutdown = GracefulTrainingShutdown(logging.getLogger("test"))
    callback = GracefulStopCallback(shutdown)
    model = DummyModel()
    callback.set_model(model)

    shutdown._handle_signal(15, None)
    callback.on_epoch_end(0)

    assert model.stop_training is True
