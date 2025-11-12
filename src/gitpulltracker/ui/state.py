"""State models used to coordinate UI rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class ChartConfig:
    """Configuration describing how charts should be rendered."""

    x_column: Optional[str]
    y_columns: List[str]
    facet_column: str
    max_panels: int
    orientation: str
    show_samples: bool
    secondary_y: List[str]

    def to_json(self) -> Dict[str, object]:
        return {
            "x_column": self.x_column,
            "y_columns": self.y_columns,
            "facet_column": self.facet_column,
            "max_panels": self.max_panels,
            "orientation": self.orientation,
            "show_samples": self.show_samples,
            "secondary_y": self.secondary_y,
        }

    @staticmethod
    def from_json(data: Dict[str, object]) -> "ChartConfig":
        return ChartConfig(
            x_column=data.get("x_column"),
            y_columns=list(data.get("y_columns", [])),
            facet_column=str(data.get("facet_column", "")),
            max_panels=int(data.get("max_panels", 4)),
            orientation=str(data.get("orientation", "vertical")),
            show_samples=bool(data.get("show_samples", False)),
            secondary_y=list(data.get("secondary_y", [])),
        )


@dataclass
class DataSliceRequest:
    """Request to render a set of charts for a particular dataset slice."""

    frame: pd.DataFrame
    config: ChartConfig
    shared_zoom: Dict[str, object]
