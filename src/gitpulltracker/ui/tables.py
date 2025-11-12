"""Reusable table components for dataset previews and summaries."""

from __future__ import annotations

from typing import List

import pandas as pd
from dash import dash_table, html


def build_column_summary_table(frame: pd.DataFrame) -> html.Div:
    """Return a table describing dataset columns."""

    summary_rows: List[dict] = []
    total_rows = len(frame)
    for column in frame.columns:
        series = frame[column]
        non_null = series.notna().sum()
        summary_rows.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "non_null": int(non_null),
                "null_pct": round(100.0 * (total_rows - non_null) / total_rows, 2) if total_rows else 0.0,
                "distinct": int(series.nunique(dropna=True)),
            }
        )

    table = dash_table.DataTable(
        data=summary_rows,
        columns=[
            {"id": "column", "name": "Column"},
            {"id": "dtype", "name": "Type"},
            {"id": "non_null", "name": "Non-null"},
            {"id": "null_pct", "name": "Null %"},
            {"id": "distinct", "name": "Distinct"},
        ],
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"padding": "0.4rem"},
        style_header={"backgroundColor": "#f3f4f6", "fontWeight": "600"},
        page_size=20,
    )

    return html.Div([html.H3("Column summary"), table])


def build_sample_table(frame: pd.DataFrame) -> html.Div:
    """Return a sample table of the first rows in the dataset."""

    preview = frame.head(25)
    table = dash_table.DataTable(
        data=preview.to_dict("records"),
        columns=[{"id": column, "name": column} for column in preview.columns],
        style_table={"overflowX": "auto"},
        page_size=25,
    )

    return html.Div([html.H3("Sample rows"), table])
