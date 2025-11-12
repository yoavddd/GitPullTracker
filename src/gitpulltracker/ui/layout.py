"""Layout helpers for the parquet investigation tool UI."""

from __future__ import annotations

from dash import dcc, html


def build_layout() -> html.Div:
    """Construct the core layout for the Dash application."""

    return html.Div(
        [
            dcc.Store(id="data-store"),
            dcc.Store(id="chart-config"),
            dcc.Store(id="shared-zoom"),
            html.Header(
                [
                    html.H1("Parquet Investigation Workbench"),
                    html.P(
                        "Upload parquet datasets, configure rich visualisations, and explore them with synchronized insights.",
                        className="tagline",
                    ),
                ],
                className="app-header",
            ),
            html.Section(
                [
                    dcc.Upload(
                        id="file-upload",
                        children=html.Div([
                            html.Span("Drag and drop a parquet file, or "),
                            html.Button("Browse", className="browse-button"),
                        ]),
                        multiple=False,
                        className="upload-area",
                    ),
                    html.Div(id="file-meta", className="file-meta"),
                ],
                className="upload-section",
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.Label("X axis"),
                            dcc.Dropdown(id="x-column", placeholder="Select a column"),
                            html.Label("Y axis columns"),
                            dcc.Dropdown(id="y-columns", multi=True, placeholder="Choose one or more columns"),
                            html.Label("Facet by"),
                            dcc.Dropdown(id="facet-column", placeholder="Optional grouping column"),
                            html.Label("Maximum charts"),
                            dcc.Input(id="max-panels", type="number", min=1, max=12, step=1, value=4),
                        ],
                        className="control-stack",
                    ),
                    html.Div(
                        [
                            html.Label("Orientation"),
                            dcc.RadioItems(
                                id="orientation",
                                options=[
                                    {"label": "Vertical", "value": "vertical"},
                                    {"label": "Horizontal", "value": "horizontal"},
                                ],
                                value="vertical",
                                inline=True,
                            ),
                            html.Label("Visual refinements"),
                            dcc.Checklist(
                                id="show-sample",
                                options=[{"label": "Show sample markers", "value": "samples"}],
                                value=["samples"],
                            ),
                            html.Label("Secondary Y axis"),
                            dcc.Dropdown(
                                id="secondary-y",
                                multi=True,
                                placeholder="Columns to align to secondary scale",
                            ),
                        ],
                        className="control-stack",
                    ),
                ],
                className="control-panel",
            ),
            html.Section(
                [
                    html.Div(id="column-summary", className="data-summary"),
                    html.Div(id="sample-table", className="data-preview"),
                ],
                className="data-section",
            ),
            html.Section(
                [
                    html.Div(
                        dcc.Loading(
                            id="chart-loader",
                            type="default",
                            children=html.Div(id="charts-container", className="charts-container"),
                        ),
                        className="charts-wrapper",
                    )
                ],
                className="charts-section",
            ),
        ],
        className="app-shell",
    )
