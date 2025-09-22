"""
Core service for filtering data.
"""

import logging
from typing import Any, Dict, List

import polars as pl

from app.api.schemas import (MovimientoAction0Filter, MovimientoAction1Filter,
                           MovimientoAction2Filter)

logger = logging.getLogger(__name__)


class FilterService:
    """
    A service for filtering Polars DataFrames based on specific, predefined logic.
    """

    def __init__(self, dataframes: Dict[str, pl.DataFrame]):
        """
        Initializes the service with the datasets.

        Args:
            dataframes: A dictionary of Polars DataFrames loaded at startup.
        """
        self.dataframes = dataframes
        logger.info(f"FilterService initialized with {len(dataframes)} datasets.")

    def _get_df(self, dataset_name: str) -> pl.DataFrame:
        """Helper to get a dataframe and raise a clear error if not found."""
        try:
            return self.dataframes[dataset_name]
        except KeyError:
            logger.error(f"Dataset '{dataset_name}' not found in FilterService.")
            raise ValueError(f"Dataset '{dataset_name}' not found.")

    def filter_movimientoaction0(self, filters: MovimientoAction0Filter) -> List[Dict[str, Any]]:
        """
        Filters the 'api_movimientoaction0' dataset.
        """
        df = self._get_df('api_movimientoaction0')

        # Build the filter expression chain
        query = (
            df.lazy()
            .filter(pl.col("OrdenanteId") == filters.OrdenanteId)
            .filter(pl.col("TipoIdOrdenante") == filters.TipoIdOrdenante)
            .filter(pl.col("Product") == filters.Product)
            .filter(pl.col("EffectiveDateStr") >= filters.EffectiveDateStart)
            .filter(pl.col("EffectiveDateStr") <= filters.EffectiveDateEnd)
            .filter(pl.col("Reference") == filters.Reference)
        )

        result_df = query.collect()
        return result_df.to_dicts()

    def filter_movimientoaction1(self, filters: MovimientoAction1Filter) -> List[Dict[str, Any]]:
        """
        Filters the 'api_movimientoaction1' dataset.
        """
        df = self._get_df('api_movimientoaction1')

        # Build the filter expression chain
        query = (
            df.lazy()
            .filter(pl.col("OrdenanteId") == filters.OrdenanteId)
            .filter(pl.col("TipoIdOrdenante") == filters.TipoIdOrdenante)
            .filter(pl.col("Product") == filters.Product)
            .filter(pl.col("EffectiveDateStr") >= filters.EffectiveDateStart)
            .filter(pl.col("EffectiveDateStr") <= filters.EffectiveDateEnd)
        )

        result_df = query.collect()
        return result_df.to_dicts()

    def filter_movimientoaction2(self, filters: MovimientoAction2Filter) -> List[Dict[str, Any]]:
        """
        Filters the 'api_movimientoaction2' dataset.
        """
        df = self._get_df('api_movimientoaction2')

        # Build the filter expression chain
        query = (
            df.lazy()
            .filter(pl.col("OrdenanteId") == filters.OrdenanteId)
            .filter(pl.col("TipoIdOrdenante") == filters.TipoIdOrdenante)
            .filter(pl.col("Product") == filters.Product)
            .filter(pl.col("EventNum") == filters.EventNum)
            .filter(pl.col("Reference") == filters.Reference)
        )

        result_df = query.collect()
        return result_df.to_dicts()
