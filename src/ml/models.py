"""
Trading EZ - Modelos Predictivos: Baseline Logit Regularizada y LightGBM Gradient Boosting.
Entrenamiento controlado con Walk-Forward, regularización estricta y estimación de R esperado.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from lightgbm import LGBMClassifier, LGBMRegressor

from src.feature_engineering.pipeline import FEATURE_COLUMNS
from src.ml.walk_forward import PurgedWalkForwardCV
from src.ml.calibration import ProbabilityCalibrator, CalibrationReport

@dataclass
class ModelMetrics:
    is_auc: float
    oos_auc: float
    auc_degradation_pct: float
    is_brier: float
    oos_brier: float
    oos_win_rate_actual: float
    calibration: CalibrationReport
    feature_importances: Dict[str, float] = field(default_factory=dict)
    is_validated: bool = False

class TradingMLPipeline:
    """
    Pipeline unificado de Machine Learning para Trading EZ.
    Combina:
    1. Clasificador LightGBM para probabilidad cruda de éxito (R > 0).
    2. Calibrador empírico de probabilidad (Isotónico / Platt).
    3. Regresor LightGBM para expectativa esperada en múltiplos de R netos.
    """

    def __init__(
        self,
        model_type: str = "lightgbm",  # "lightgbm" | "logit"
        calibration_method: str = "isotonic",
        random_state: int = 42,
    ):
        self.model_type = model_type
        self.calibration_method = calibration_method
        self.random_state = random_state

        # Clasificador principal
        if model_type == "logit":
            self.classifier = Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(C=0.1, penalty="l2", solver="lbfgs", max_iter=500, random_state=random_state)),
            ])
        else:
            self.classifier = LGBMClassifier(
                n_estimators=100,
                learning_rate=0.03,
                max_depth=4,
                num_leaves=15,
                min_child_samples=30,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=0.1,
                random_state=random_state,
                verbose=-1,
            )

        # Regresor secundario para R esperado
        self.regressor = LGBMRegressor(
            n_estimators=80,
            learning_rate=0.03,
            max_depth=3,
            num_leaves=10,
            min_child_samples=30,
            random_state=random_state,
            verbose=-1,
        )

        self.calibrator = ProbabilityCalibrator(method=calibration_method)
        self.is_fitted = False
        self.metrics: Optional[ModelMetrics] = None

    def train_and_validate(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        target_col: str = "target_winner",
        target_r_col: str = "target_r_net",
        n_splits: int = 4,
    ) -> ModelMetrics:
        """
        Ejecuta validación Walk-Forward con purga y embargo sobre el dataset histórico.
        Evalúa honestamente el rendimiento fuera de muestra y la degradación in-sample -> out-of-sample.
        """
        feats = feature_cols or [c for c in FEATURE_COLUMNS if c in df.columns]

        # Filtrar filas válidas (que tengan target calculado)
        valid_df = df.dropna(subset=[target_col, target_r_col] + feats).copy()
        if len(valid_df) < 200:
            raise ValueError(f"Datos insuficientes para entrenamiento: {len(valid_df)} barras válidas.")

        X = valid_df[feats].values
        y = valid_df[target_col].values.astype(int)
        y_r = valid_df[target_r_col].values.astype(float)

        cv = PurgedWalkForwardCV(n_splits=n_splits, train_ratio=0.60, purge_bars=15, embargo_bars=5)

        oos_preds_raw = []
        oos_y_true = []
        is_preds_raw = []
        is_y_true = []

        # 1. Validación cruzada Walk-Forward
        for train_idx, test_idx in cv.split(valid_df):
            X_tr, y_tr = X[train_idx], y[train_idx]
            X_te, y_te = X[test_idx], y[test_idx]

            # Entrenar clasificador temporal
            if self.model_type == "logit":
                fold_clf = Pipeline([
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(C=0.1, penalty="l2", solver="lbfgs", max_iter=500)),
                ])
            else:
                fold_clf = LGBMClassifier(
                    n_estimators=80, learning_rate=0.03, max_depth=4, num_leaves=15,
                    min_child_samples=25, subsample=0.8, colsample_bytree=0.8,
                    reg_alpha=0.1, reg_lambda=0.1, random_state=self.random_state, verbose=-1,
                )

            fold_clf.fit(X_tr, y_tr)

            # Predicciones In-Sample
            p_tr = fold_clf.predict_proba(X_tr)[:, 1]
            is_preds_raw.extend(p_tr)
            is_y_true.extend(y_tr)

            # Predicciones Out-of-Sample
            p_te = fold_clf.predict_proba(X_te)[:, 1]
            oos_preds_raw.extend(p_te)
            oos_y_true.extend(y_te)

        oos_preds_arr = np.array(oos_preds_raw)
        oos_y_arr = np.array(oos_y_true)
        is_preds_arr = np.array(is_preds_raw)
        is_y_arr = np.array(is_y_true)

        # 2. Ajustar calibrador exclusivamente sobre predicciones OOS
        self.calibrator.fit(oos_preds_arr, oos_y_arr)
        oos_calibrated = self.calibrator.predict_calibrated(oos_preds_arr)

        cal_report = self.calibrator.evaluate_calibration(oos_y_arr, oos_calibrated)

        from sklearn.metrics import roc_auc_score, brier_score_loss
        is_auc = float(roc_auc_score(is_y_arr, is_preds_arr)) if len(np.unique(is_y_arr)) > 1 else 0.50
        oos_auc = cal_report.auc_roc
        degradation = ((is_auc - oos_auc) / is_auc * 100.0) if is_auc > 0 else 0.0

        is_brier = float(brier_score_loss(is_y_arr, is_preds_arr))
        oos_brier = cal_report.brier_score

        # 3. Entrenar modelo final sobre todo el dataset
        self.classifier.fit(X, y)
        self.regressor.fit(X, y_r)
        self.is_fitted = True

        # Importancia de características
        feature_imp: Dict[str, float] = {}
        if hasattr(self.classifier, "feature_importances_"):
            raw_imp = self.classifier.feature_importances_
            total = float(np.sum(raw_imp)) or 1.0
            for name, imp in zip(feats, raw_imp):
                feature_imp[name] = round(float(imp) / total, 4)

        # Regla estricta: Validado si Brier OOS < 0.245 y OOS AUC > 0.52
        is_validated = cal_report.is_calibrated and (oos_auc >= 0.52)

        self.metrics = ModelMetrics(
            is_auc=round(is_auc, 4),
            oos_auc=round(oos_auc, 4),
            auc_degradation_pct=round(degradation, 2),
            is_brier=round(is_brier, 4),
            oos_brier=round(oos_brier, 4),
            oos_win_rate_actual=round(float(np.mean(oos_y_arr)), 4),
            calibration=cal_report,
            feature_importances=feature_imp,
            is_validated=is_validated,
        )

        return self.metrics

    def predict_opportunity(self, features_dict: Dict[str, float]) -> Tuple[float, float]:
        """
        Predice para una barra individual:
        Retorna (probabilidad_calibrada, r_esperado_neto).
        """
        if not self.is_fitted:
            raise ValueError("El pipeline no ha sido entrenado todavía.")

        feats = [features_dict.get(col, 0.0) for col in FEATURE_COLUMNS]
        X_vec = np.array([feats])

        # Probabilidad cruda
        raw_prob = float(self.classifier.predict_proba(X_vec)[0, 1])

        # Probabilidad calibrada
        cal_prob = float(self.calibrator.predict_calibrated(np.array([raw_prob]))[0])

        # R esperado
        expected_r = float(self.regressor.predict(X_vec)[0])

        return cal_prob, expected_r
