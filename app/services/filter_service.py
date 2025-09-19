"""
Core service for filtering data and managing the in-memory cache.
"""

import logging
from functools import reduce
from typing import Any, Dict, List, Tuple

import polars as pl
from polars.exceptions import ColumnNotFoundError

logger = logging.getLogger(__name__)

# Define non-deprecated type groups for casting checks
INTEGER_TYPES = (pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64)
FLOAT_TYPES = (pl.Float32, pl.Float64)


class FilterService:
    """
    A service for filtering Polars DataFrames with an in-memory cache.

    This class holds the loaded datasets and provides a method to filter them
    based on dynamic query parameters. It uses a simple dictionary-based cache
    to store and retrieve results for identical queries, significantly
    improving performance for repeated requests.
    """

    def __init__(self, dataframes: Dict[str, pl.DataFrame]):
        """
        Initializes the service with the datasets and an empty cache.

        Args:
            dataframes: A dictionary of Polars DataFrames loaded at startup.
        """
        self.dataframes = dataframes
        # Cache format: {(dataset_name, frozenset_of_filters): result_list}
        self._cache: Dict[Tuple[str, frozenset], List[Dict[str, Any]]] = {}
        logger.info(f"FilterService initialized with {len(dataframes)} datasets.")

    def _get_cache_key(self, dataset_name: str, filters: Dict[str, Any]) -> Tuple[str, frozenset]:
        """Creates a hashable cache key from the dataset name and filters."""
        # A frozenset of the dict's items is hashable and order-independent.
        return (dataset_name, frozenset(filters.items()))

    def _apply_filters(self, df: pl.DataFrame, filters: Dict[str, Any]) -> pl.DataFrame:
        """
        Applies a set of filters to a Polars DataFrame.

        This method dynamically builds a Polars filter expression based on
        a dictionary of filter conditions. It supports suffixes like `_min`
        and `_max` for range filtering and handles data type casting.

        Args:
            df: The Polars DataFrame to filter.
            filters: A dictionary of filter conditions.

        Returns:
            The filtered Polars DataFrame.

        Raises:
            ValueError: If a filter is invalid (e.g., bad column name or value).
        """
        if not filters:
            return df

        expressions = []
        for key, raw_value in filters.items():
            if key.endswith("_min"):
                col_name, op = key[:-4], "ge"
            elif key.endswith("_max"):
                col_name, op = key[:-4], "le"
            else:
                col_name, op = key, "eq"

            if col_name not in df.columns:
                raise ValueError(f"Invalid filter: Column '{col_name}' does not exist.")

            try:
                col_type = df.schema[col_name]

                if str(raw_value).lower() in ['null', 'none', '']:
                    typed_value = None
                elif isinstance(col_type, INTEGER_TYPES):
                    typed_value = int(raw_value)
                elif isinstance(col_type, FLOAT_TYPES):
                    typed_value = float(raw_value)
                elif isinstance(col_type, pl.Boolean):
                    typed_value = str(raw_value).lower() in ['true', '1', 't', 'y', 'yes']
                else: # Handles String, Categorical, etc. by default
                    typed_value = raw_value
            except (ValueError, TypeError):
                raise ValueError(f"Invalid value for column '{col_name}': could not cast '{raw_value}'.")

            column_expr = pl.col(col_name)
            if op == "ge":
                expressions.append(column_expr >= typed_value)
            elif op == "le":
                expressions.append(column_expr <= typed_value)
            elif op == "eq":
                expressions.append(column_expr.is_null() if typed_value is None else column_expr == typed_value)

        if not expressions:
            return df

        combined_filter = reduce(lambda a, b: a & b, expressions)
        return df.filter(combined_filter)

    def filter_dataframe(
        self, dataset_name: str, filters: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Filters a dataset based on query parameters and uses an in-memory cache.

        Args:
            dataset_name: The name of the dataset to filter.
            filters: A dictionary of filter conditions from the query parameters.

        Returns:
            A tuple containing:
            - A list of dictionaries representing the filtered rows.
            - A boolean indicating if the result was from the cache (`True` for hit).

        Raises:
            KeyError: If the requested dataset does not exist.
            ValueError: If the filters are invalid.
        """
        if dataset_name not in self.dataframes:
            raise KeyError(f"Dataset '{dataset_name}' not found.")

        cache_key = self._get_cache_key(dataset_name, filters)

        if cache_key in self._cache:
            logger.info(f"Cache HIT for dataset '{dataset_name}' with filters: {filters}")
            return self._cache[cache_key], True

        logger.info(f"Cache MISS for dataset '{dataset_name}' with filters: {filters}")

        df = self.dataframes[dataset_name]

        try:
            filtered_df = self._apply_filters(df, filters)
            result = filtered_df.to_dicts()

            self._cache[cache_key] = result
            logger.info(f"Filter successful. Rows returned: {len(result)}. Result cached.")

            return result, False
        except (ValueError, ColumnNotFoundError, TypeError) as e:
            logger.warning(f"Filtering failed for dataset '{dataset_name}': {e}")
            raise ValueError(str(e)) from e
