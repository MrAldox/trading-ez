"""
Trading EZ - Particionado Temporal: Walk-Forward Cross-Validation con Purga y Embargo.
Prohibición absoluta de K-Fold aleatorio. Garantiza evaluación estrictamente fuera de muestra.
"""
from __future__ import annotations
from typing import Generator, List, Tuple
import numpy as np
import pandas as pd

class PurgedWalkForwardCV:
    """
    Generador de particiones temporales Walk-Forward con Purga y Embargo (Marcos López de Prado).
    - Train se desliza o expande hacia adelante en el tiempo.
    - Test evalúa siempre sobre el periodo inmediatamente posterior.
    - Purga: descarta las últimas 'purge_bars' del conjunto train para que las operaciones
      de triple barrera abiertas al final del train no se solapen con el inicio de test.
    - Embargo: descarta 'embargo_bars' al inicio de test para evitar autocorrelación serial.
    """

    def __init__(
        self,
        n_splits: int = 5,
        train_ratio: float = 0.65,
        purge_bars: int = 15,
        embargo_bars: int = 5,
        expanding: bool = True,
    ):
        self.n_splits = n_splits
        self.train_ratio = train_ratio
        self.purge_bars = purge_bars
        self.embargo_bars = embargo_bars
        self.expanding = expanding

    def split(self, df: pd.DataFrame) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        n = len(df)
        if n < 200:
            raise ValueError(f"Se requieren al menos 200 barras para Walk-Forward, recibido {n}")

        indices = np.arange(n)

        # Tamaño inicial de train y paso de cada fold de test
        initial_train_size = int(n * self.train_ratio)
        test_total_size = n - initial_train_size
        test_step = max(test_total_size // self.n_splits, 20)

        for i in range(self.n_splits):
            test_start = initial_train_size + (i * test_step) + self.embargo_bars
            test_end = min(initial_train_size + ((i + 1) * test_step), n)

            if test_start >= n or test_start >= test_end:
                break

            train_start = 0 if self.expanding else max(0, test_start - initial_train_size)
            # Purgar el final de train
            train_end = max(train_start + 50, test_start - self.embargo_bars - self.purge_bars)

            train_indices = indices[train_start:train_end]
            test_indices = indices[test_start:test_end]

            if len(train_indices) < 50 or len(test_indices) < 10:
                continue

            yield train_indices, test_indices
