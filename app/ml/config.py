from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config.settings import settings


@dataclass(frozen=True)
class MLConfig:
    enabled: bool = True
    min_training_events: int = 20
    n_estimators: int = 100
    contamination: str | float = "auto"
    random_state: int = 42
    anomaly_threshold: float = 0.70
    model_version: str = "v1"
    feature_version: str = "v1"
    model_dir: Path = Path("data/models")

    @classmethod
    def from_settings(cls) -> "MLConfig":
        return cls(
            enabled=settings.ml_enabled,
            min_training_events=settings.ml_min_training_events,
            n_estimators=settings.ml_n_estimators,
            contamination=settings.ml_contamination,
            random_state=settings.ml_random_state,
            anomaly_threshold=settings.ml_anomaly_threshold,
            model_version=settings.ml_model_version,
            feature_version=settings.ml_feature_version,
            model_dir=Path(settings.ml_model_dir),
        )


ml_config = MLConfig.from_settings()
