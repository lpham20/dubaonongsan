from __future__ import annotations

import logging
import signal

import tensorflow as tf


class GracefulTrainingShutdown:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.stop_requested = False
        self.signal_name: str | None = None

    def install(self) -> None:
        for signal_name in ("SIGINT", "SIGTERM"):
            signum = getattr(signal, signal_name, None)
            if signum is None:
                continue
            signal.signal(signum, self._handle_signal)

    def _handle_signal(self, signum: int, _frame: object) -> None:
        name = signal.Signals(signum).name
        if self.stop_requested:
            raise KeyboardInterrupt(f"Second {name} received; aborting training immediately.")
        self.stop_requested = True
        self.signal_name = name
        self.logger.warning("Received %s; training will stop after the current epoch and save completed state.", name)


class GracefulStopCallback(tf.keras.callbacks.Callback):
    def __init__(self, shutdown: GracefulTrainingShutdown) -> None:
        super().__init__()
        self.shutdown = shutdown

    def on_epoch_end(self, epoch: int, logs: dict | None = None) -> None:
        if self.shutdown.stop_requested:
            self.model.stop_training = True
            self.shutdown.logger.warning("Stopped training gracefully after epoch %s.", epoch + 1)
