"""
Servicio principal para el filtrado de datos.
"""

import logging
from typing import Any, Dict, List

import polars as pl

from app.api.schemas import (MovimientoAction0Filter, MovimientoAction1Filter,
                           MovimientoAction2Filter)

logger = logging.getLogger(__name__)


class FilterService:
    """
    Un servicio para filtrar DataFrames de Polars basado en una lógica específica y predefinida.
    """

    def __init__(self, dataframes: Dict[str, pl.DataFrame]):
        """
        Inicializa el servicio con los conjuntos de datos.

        Args:
            dataframes: Un diccionario de DataFrames de Polars cargados al inicio.
        """
        self.dataframes = dataframes
        logger.info(f"FilterService inicializado con {len(dataframes)} conjuntos de datos.")

    def _get_df(self, dataset_name: str) -> pl.DataFrame:
        """Función auxiliar para obtener un dataframe y lanzar un error claro si no se encuentra."""
        try:
            return self.dataframes[dataset_name]
        except KeyError:
            logger.error(f"El conjunto de datos '{dataset_name}' no se encontró en FilterService.")
            raise ValueError(f"No se encontró el conjunto de datos '{dataset_name}'.")

    def filter_movimientoaction0(self, filters: MovimientoAction0Filter) -> List[Dict[str, Any]]:
        """
        Filtra el conjunto de datos 'api_movimientoaction0'.
        """
        df = self._get_df('api_movimientoaction0')

        # Construye la cadena de expresiones de filtro
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
        Filtra el conjunto de datos 'api_movimientoaction1'.
        """
        df = self._get_df('api_movimientoaction1')

        # Construye la cadena de expresiones de filtro
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
        Filtra el conjunto de datos 'api_movimientoaction2'.
        """
        df = self._get_df('api_movimientoaction2')

        # Construye la cadena de expresiones de filtro
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
