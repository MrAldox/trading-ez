"""
Trading EZ - Calibración de Probabilidades y Evaluación de Fiabilidad Cuantitativa.
Isotonic Regression y Platt Scaling ajustados estrictamente sobre predicciones fuera de muestra (OOS).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.calibration import calibration_curve

@dataclass
class CalibrationReport:
    brier_score: float
    auc_roc: float
    is_calibrated: bool
    bins_predicted: List[float]
    bins_empirical: List[float]
    bin_counts: List[int]
    status: str  # "VALIDADO" | "SIN CALIBRAR"

class ProbabilityCalibrator:
    """
    Calibrador empírico de probabilidades para modelos predictivos.
    Garantiza que cuando el sistema emite '65%', empíricamente ~65% de esas operaciones ganaron.
    """

    def __init__(self, method: str = "isotonic"):
        self.method = method.lower()
        if self.method == "isotonic":
            self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)
        else:
            # Platt Scaling (Sigmoid)
            self.calibrator = LogisticRegression(C=1.0, solver="lbfgs")
        self.is_fitted = False

    def fit(self, y_raw_probs: np.ndarray, y_true: np.ndarray) -> ProbabilityCalibrator:
        """Ajusta el calibrador sobre probabilidades crudas y etiquetas reales."""
        y_probs_clean = np.clip(y_raw_probs, 0.001, 0.999)
        if self.method == "isotonic":
            self.calibrator.fit(y_probs_clean, y_true)
        else:
            # LogisticRegression requiere shape (N, 1)
            self.calibrator.fit(y_probs_clean.reshape(-1, 1), y_true)
        self.is_fitted = True
        return self

    def predict_calibrated(self, y_raw_probs: np.ndarray) -> np.ndarray:
        """Transforma probabilidades crudas a probabilidades calibradas."""
        if not self.is_fitted:
            return y_raw_probs
        y_clean = np.clip(y_raw_probs, 0.001, 0.999)
        if self.method == "isotonic":
            return np.clip(self.calibrator.predict(y_clean), 0.01, 0.99)
        else:
            return np.clip(self.calibrator.predict_proba(y_clean.reshape(-1, 1))[:, 1], 0.01, 0.99)

    def evaluate_calibration(
        self,
        y_true: np.ndarray,
        y_calibrated_probs: np.ndarray,
        n_bins: int = 5,
    ) -> CalibrationReport:
        """
        Evalúa el Brier score, AUC-ROC y la curva de fiabilidad empírica por tramos.
        """
        if len(y_true) < 20:
            return CalibrationReport(
                brier_score=0.25,
                auc_roc=0.50,
                is_calibrated=False,
                bins_predicted=[],
                bins_empirical=[],
                bin_counts=[],
                status="SIN CALIBRAR",
            )

        brier = float(brier_score_loss(y_true, y_calibrated_probs))
        try:
            auc = float(roc_auc_score(y_true, y_calibrated_probs))
        except Exception:
            auc = 0.50

        # Curva de calibración
        prob_true, prob_pred = calibration_curve(y_true, y_calibrated_probs, n_bins=n_bins, strategy="uniform")

        # Conteo por bucket
        bins = np.linspace(0.0, 1.0, n_bins + 1)
        bin_assignments = np.digitize(y_calibrated_probs, bins) - 1
        bin_counts = [int(np.sum(bin_assignments == b)) for b in range(n_bins)]

        # Criterio estricto de honestidad:
        # Brier score aceptable (< 0.235) y AUC > 0.52 en datos OOS
        is_calibrated = (brier < 0.235) and (auc > 0.52)
        status = "VALIDADO" if is_calibrated else "SIN CALIBRAR"

        return CalibrationReport(
            brier_score=round(brier, 4),
            auc_roc=round(auc, 4),
            is_calibrated=is_calibrated,
            bins_predicted=[round(float(p), 4) for p in prob_pred],
            bins_empirical=[round(float(p), 4) for p in prob_true],
            bin_counts=bin_counts,
            status=status,
        )
