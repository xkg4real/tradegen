"""DataHandlerLP, DatasetH, TSDatasetH, Labels & Leak-Free Processor Chains (Pillar 2)."""
from __future__ import annotations

from qlib_lab.data.dataset import (
    Dataset,
    DatasetH,
    TSDataSampler,
    TSDatasetH,
    authorized_eval_context,
    is_eval_authorized,
)
from qlib_lab.data.handler import DataHandler, DataHandlerLP, fetch_df_by_col, fetch_df_by_index
from qlib_lab.data.labels import (
    CLASS_TO_ID,
    DIRECTION_CLASSES,
    ID_TO_CLASS,
    PurgedHorizonReturnLabel,
)
from qlib_lab.data.loader import (
    DataLoader,
    ExpressionDataLoader,
    StaticDataLoader,
    ensure_grouped_columns,
    normalize_panel_index,
)
from qlib_lab.data.processors import (
    CSRankNorm,
    CSZScoreNorm,
    DropnaLabelProcessor,
    ExplicitFillnaProcessor,
    FailClosedDropnaProcessor,
    Processor,
    RobustZScoreNorm,
    StandardZScoreNorm,
    StatefulProcessor,
    WinsorizeClip,
)

__all__ = [
    "CLASS_TO_ID",
    "CSRankNorm",
    "CSZScoreNorm",
    "DIRECTION_CLASSES",
    "DataHandler",
    "DataHandlerLP",
    "DataLoader",
    "Dataset",
    "DatasetH",
    "DropnaLabelProcessor",
    "ExplicitFillnaProcessor",
    "ExpressionDataLoader",
    "FailClosedDropnaProcessor",
    "ID_TO_CLASS",
    "Processor",
    "PurgedHorizonReturnLabel",
    "RobustZScoreNorm",
    "StandardZScoreNorm",
    "StatefulProcessor",
    "StaticDataLoader",
    "TSDataSampler",
    "TSDatasetH",
    "WinsorizeClip",
    "authorized_eval_context",
    "ensure_grouped_columns",
    "fetch_df_by_col",
    "fetch_df_by_index",
    "is_eval_authorized",
    "normalize_panel_index",
]
