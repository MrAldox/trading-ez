"""
Trading EZ - Tests Unitarios de Calibración de Probabilidades y Brier Score (Fase 3).
"""
import pytest
import numpy as np

from src.ml.calibration import ProbabilityCalibrator

def test_calibrator_fits_and_improves_probabilities():
    np.random.seed(42)
    # Generar probabilidades crudas sobreconfiadas
    n = 200
    y_true = np.random.binomial(1, 0.55, size=n)
    raw_probs = np.clip(y_true * 0.7 + np.random.normal(0, 0.2, size=n), 0.05, 0.95)

    calibrator = ProbabilityCalibrator(method="isotonic")
    calibrator.fit(raw_probs, y_true)
    assert calibrator.is_fitted is True

    calibrated_probs = calibrator.predict_calibrated(raw_probs)
    assert len(calibrated_probs) == n
    assert (calibrated_probs >= 0.0).all() and (calibrated_probs <= 1.0).all()

    report = calibrator.evaluate_calibration(y_true, calibrated_probs, n_bins=5)
    assert report.brier_score < 0.25
    assert len(report.bins_predicted) > 0
    assert len(report.bins_empirical) > 0

def test_uncalibrated_or_random_model_marked_uncalibrated():
    # Modelo totalmente ruidoso evaluado fuera de muestra
    np.random.seed(99)
    n_train, n_test = 200, 200
    y_train = np.random.binomial(1, 0.50, size=n_train)
    noisy_train = np.random.uniform(0.1, 0.9, size=n_train)

    y_test = np.random.binomial(1, 0.50, size=n_test)
    noisy_test = np.random.uniform(0.1, 0.9, size=n_test)

    calibrator = ProbabilityCalibrator(method="isotonic")
    calibrator.fit(noisy_train, y_train)
    calibrated_test = calibrator.predict_calibrated(noisy_test)

    report = calibrator.evaluate_calibration(y_test, calibrated_test)
    # Al no tener ventaja estadística en datos no vistos, no debe ser validado
    assert report.is_calibrated is False
    assert report.status == "SIN CALIBRAR"
