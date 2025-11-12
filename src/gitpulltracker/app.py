"""Dash application factory for the parquet investigation tool."""

from __future__ import annotations

import base64
import io
import json
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Dash, Input, Output, State, callback_context, dcc, html, no_update
from plotly.subplots import make_subplots

from .ui.layout import build_layout
from .ui.state import ChartConfig, DataSliceRequest
from .ui.tables import build_column_summary_table, build_sample_table


@dataclass
class UploadedData:
    """Container for uploaded dataframe metadata."""

    name: str
    rows: int
    columns: int
    data: pd.DataFrame

    def to_json(self) -> str:
        return json.dumps(
            {
                "name": self.name,
                "rows": self.rows,
                "columns": self.columns,
                "data": self.data.to_json(date_format="iso", orient="split"),
            }
        )

    @staticmethod
    def from_json(data: str) -> "UploadedData":
        payload = json.loads(data)
        frame = pd.read_json(payload["data"], orient="split")
        return UploadedData(
            name=payload["name"],
            rows=payload["rows"],
            columns=payload["columns"],
            data=frame,
        )


def create_app() -> Dash:
    """Create and configure the Dash application."""

    app = Dash(__name__)
    app.title = "Parquet Investigation Workbench"
    app.layout = build_layout()

    register_callbacks(app)

    return app


def register_callbacks(app: Dash) -> None:
    """Attach all Dash callbacks to the application instance."""

    @app.callback(
        Output("data-store", "data"),
        Output("file-meta", "children"),
        Input("file-upload", "contents"),
        State("file-upload", "filename"),
        prevent_initial_call=True,
    )
    def handle_upload(contents: Optional[str], filename: Optional[str]):
        if contents is None or filename is None:
            return no_update, no_update

        content_type, content_string = contents.split(",", 1)
        if "parquet" not in content_type and not filename.lower().endswith(".parquet"):
            return no_update, html.Div(
                [
                    html.P("Unsupported file type. Please provide a parquet file."),
                ],
                className="error-message",
            )

        decoded = base64.b64decode(content_string)
        buffer = io.BytesIO(decoded)
        data_frame = pd.read_parquet(buffer)

        uploaded = UploadedData(
            name=filename,
            rows=int(data_frame.shape[0]),
            columns=int(data_frame.shape[1]),
            data=data_frame,
        )

        metadata = html.Div(
            [
                html.H3(filename, className="file-name"),
                html.P(f"Rows: {uploaded.rows:,} | Columns: {uploaded.columns}"),
            ],
            className="file-metadata",
        )

        return uploaded.to_json(), metadata

    @app.callback(
        Output("column-summary", "children"),
        Output("sample-table", "children"),
        Output("x-column", "options"),
        Output("y-columns", "options"),
        Output("facet-column", "options"),
        Output("secondary-y", "options"),
        Input("data-store", "data"),
    )
    def populate_data_views(data_json: Optional[str]):
        if not data_json:
            empty_options: List[dict] = []
            return (
                html.Div(className="placeholder"),
                html.Div(className="placeholder"),
                empty_options,
                empty_options,
                empty_options,
                empty_options,
            )

        uploaded = UploadedData.from_json(data_json)
        frame = uploaded.data

        column_summary = build_column_summary_table(frame)
        sample_table = build_sample_table(frame)

        options = [
            {"label": name, "value": name}
            for name in frame.columns
        ]

        return column_summary, sample_table, options, options, options, options

    @app.callback(
        Output("chart-config", "data"),
        Input("x-column", "value"),
        Input("y-columns", "value"),
        Input("facet-column", "value"),
        Input("max-panels", "value"),
        Input("orientation", "value"),
        Input("show-sample", "value"),
        Input("secondary-y", "value"),
    )
    def update_chart_config(
        x_column: Optional[str],
        y_columns: Optional[List[str]],
        facet_column: Optional[str],
        max_panels: Optional[int],
        orientation: str,
        show_sample: Optional[List[str]],
        secondary_y: Optional[List[str]],
    ):
        sanitized_y = (y_columns or [])
        sanitized_secondary = [col for col in (secondary_y or []) if col in sanitized_y]
        panels_value = int(max_panels or 4)
        panels_value = max(1, min(12, panels_value))

        config = ChartConfig(
            x_column=x_column,
            y_columns=sanitized_y,
            facet_column=facet_column or "",
            max_panels=panels_value,
            orientation=orientation,
            show_samples=bool(show_sample),
            secondary_y=sanitized_secondary,
        )
        return config.to_json()

    @app.callback(
        Output("charts-container", "children"),
        Input("data-store", "data"),
        Input("chart-config", "data"),
        Input("shared-zoom", "data"),
    )
    def render_charts(data_json: Optional[str], chart_config_json: Optional[str], shared_zoom: Optional[dict]):
        if not data_json or not chart_config_json:
            return html.Div(
                [html.P("Upload a parquet file and configure chart options to begin.")],
                className="placeholder",
            )

        uploaded = UploadedData.from_json(data_json)
        config = ChartConfig.from_json(chart_config_json)

        if not config.x_column or not config.y_columns:
            return html.Div(
                [html.P("Select an x-axis and at least one y-axis column to visualize.")],
                className="placeholder",
            )

        if config.x_column not in uploaded.data.columns:
            return html.Div(
                [html.P("Selected x-axis column is no longer available in the dataset.")],
                className="error-message",
            )

        missing_y = [col for col in config.y_columns if col not in uploaded.data.columns]
        if missing_y:
            return html.Div(
                [html.P(f"Columns missing from dataset: {', '.join(missing_y)}")],
                className="error-message",
            )

        request = DataSliceRequest(
            frame=uploaded.data,
            config=config,
            shared_zoom=shared_zoom or {},
        )

        charts = build_chart_group(request)

        return charts

    @app.callback(
        Output("shared-zoom", "data"),
        Input({"type": "facet-graph", "index": ALL}, "relayoutData"),
        State("shared-zoom", "data"),
        prevent_initial_call=True,
    )
    def capture_zoom(relayout_events: List[Optional[dict]], current_zoom: Optional[dict]):
        if not callback_context.triggered:
            return no_update

        event = callback_context.triggered[0]
        data = event.get("value") if isinstance(event, dict) else None
        if not isinstance(data, dict) or not data:
            return no_update

        if data.get("xaxis.autorange"):
            return {"mode": "autorange", "timestamp": time.time()}

        range_start = data.get("xaxis.range[0]")
        range_end = data.get("xaxis.range[1]")
        if range_start is None or range_end is None:
            return no_update

        return {
            "mode": "range",
            "range": [range_start, range_end],
            "timestamp": time.time(),
        }


def build_chart_group(request: DataSliceRequest) -> html.Div:
    """Render the collection of charts for the current request."""

    frame = request.frame
    config = request.config

    facet_values: Iterable[Optional[str]]
    if config.facet_column and config.facet_column in frame.columns:
        unique_values = frame[config.facet_column].dropna().unique().tolist()
        facet_values = unique_values[: config.max_panels]
        if not facet_values:
            facet_values = [None]
    else:
        facet_values = [None]

    orientation_style = {
        "display": "flex",
        "flexDirection": "column" if config.orientation == "vertical" else "row",
        "flexWrap": "wrap",
        "gap": "1.5rem",
    }

    graphs: List[html.Div] = []
    for idx, facet_value in enumerate(facet_values):
        subset = frame if facet_value is None else frame[frame[config.facet_column] == facet_value]
        figure = build_figure(subset, config, facet_value, request.shared_zoom)
        graphs.append(
            html.Div(
                [
                    html.H4(
                        f"{config.facet_column} = {facet_value}" if facet_value is not None else "Combined View",
                        className="chart-title",
                    ),
                    dcc.Graph(
                        id={"type": "facet-graph", "index": idx},
                        figure=figure,
                        className="chart",
                        config={
                            "displaylogo": False,
                            "modeBarButtonsToAdd": [
                                "drawline",
                                "drawopenpath",
                                "drawrect",
                                "eraseshape",
                            ],
                        },
                    ),
                ],
                className="chart-container",
            )
        )

    return html.Div(graphs, style=orientation_style, className="chart-group")


def build_figure(
    frame: pd.DataFrame,
    config: ChartConfig,
    facet_value: Optional[str],
    shared_zoom: dict,
) -> go.Figure:
    """Create a Plotly figure for a single facet."""

    secondary_set = set(config.secondary_y)
    figure = make_subplots(specs=[[{"secondary_y": bool(secondary_set)}]])

    # Sort by x-axis for readability when possible.
    if config.x_column in frame.columns:
        frame = frame.sort_values(config.x_column)

    for column in config.y_columns:
        if column not in frame.columns:
            continue
        series = frame[column]
        x_values = frame[config.x_column]
        is_secondary = column in secondary_set
        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=series,
                mode="lines",
                name=column,
                hovertemplate="%{y}<extra>" + column + "</extra>",
            ),
            secondary_y=is_secondary,
        )
        if config.show_samples:
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=series,
                    mode="markers",
                    marker={"size": 6, "opacity": 0.5},
                    name=f"{column} samples",
                    hovertemplate="%{y}<extra>" + column + " sample</extra>",
                    showlegend=False,
                ),
                secondary_y=is_secondary,
            )

    figure.update_layout(
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        hovermode="x unified",
        margin={"l": 60, "r": 60, "t": 40, "b": 40},
        uirevision="shared",
    )

    figure.update_xaxes(title=config.x_column)
    figure.update_yaxes(title="Primary scale", secondary_y=False)
    if secondary_set:
        figure.update_yaxes(title="Secondary scale", secondary_y=True)

    if shared_zoom:
        if shared_zoom.get("mode") == "range" and shared_zoom.get("range"):
            figure.update_xaxes(range=shared_zoom["range"])
        elif shared_zoom.get("mode") == "autorange":
            figure.update_xaxes(autorange=True)

    if facet_value is not None:
        figure.update_layout(title_text=str(facet_value))

    return figure


def main() -> None:
    """Run the Dash development server."""

    create_app().run_server(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()
