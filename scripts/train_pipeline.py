"""
Trading EZ - Script CLI de Entrenamiento, Calibración y Registro del Modelo Campeón (Fase 3).
Entrena con 5+ años de histórico, valida fuera de muestra con Walk-Forward y purga/embargo,
calibra con Isotonic Regression y registra artefactos serializados.
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.core.config import settings
from src.data_providers.cache_manager import CacheManager
from src.feature_engineering.pipeline import build_features, FEATURE_COLUMNS
from src.ml.labeling import TripleBarrierLabeler
from src.ml.models import TradingMLPipeline
from src.ml.registry import model_registry

def load_universe_dataset(symbols: list[str]) -> pd.DataFrame:
    """Carga y procesa características y etiquetas para la lista de activos."""
    cm = CacheManager()
    all_dfs = []

    # Cargar benchmark SPY para contexto
    spy_res = cm.get_daily("SPY")
    bench_df = spy_res[0] if spy_res else None

    labeler = TripleBarrierLabeler(
        atr_multiplier=1.5,
        target_r=1.5,
        max_holding_bars=10,
        est_cost_bps=10.0,
    )

    print(f"Construyendo dataset histórico para {len(symbols)} activos...")
    for sym in symbols:
        res = cm.get_daily(sym)
        if not res:
            continue
        df, _ = res
        if len(df) < 250:
            continue

        # 1. Características causales
        feat_df = build_features(df, benchmark_df=bench_df, benchmark_name="SPY")

        # 2. Triple barrera
        labeled_df = labeler.label_dataset(feat_df)
        labeled_df["symbol"] = sym

        all_dfs.append(labeled_df)

    if not all_dfs:
        raise ValueError("No se encontraron datos en caché para los activos solicitados.")

    combined = pd.concat(all_dfs).sort_index()
    return combined

def main():
    print("=" * 75)
    print("  TRADING EZ - ENTRENAMIENTO CUANTITATIVO, CALIBRACIÓN Y VALIDACIÓN OOS")
    print("=" * 75)

    universe_symbols = [a.symbol for a in settings.universe]
    combined_df = load_universe_dataset(universe_symbols)

    valid_mask = ~combined_df["target_winner"].isna()
    train_data = combined_df[valid_mask]

    start_date = train_data.index[0].strftime("%Y-%m-%d")
    end_date = train_data.index[-1].strftime("%Y-%m-%d")
    total_samples = len(train_data)

    print(f"Total de observaciones con triple barrera: {total_samples}")
    print(f"Rango temporal total: {start_date} a {end_date}")
    print(f"Tasa base de acierto (win rate bruto universo): {train_data['target_winner'].mean() * 100:.1f}%\n")

    # Inicializar pipeline LightGBM
    pipeline = TradingMLPipeline(
        model_type="lightgbm",
        calibration_method=settings.ml.calibration_method,
    )

    print("Iniciando Walk-Forward Cross Validation con Purga y Embargo...")
    metrics = pipeline.train_and_validate(train_data, n_splits=settings.ml.walk_forward_splits)

    print("\n" + "=" * 75)
    print("  RESULTADOS DE VALIDACIÓN FUERA DE MUESTRA (OUT-OF-SAMPLE)")
    print("=" * 75)
    print(f"AUC In-Sample (IS):            {metrics.is_auc:.4f}")
    print(f"AUC Fuera de Muestra (OOS):     {metrics.oos_auc:.4f}")
    print(f"Degradación IS -> OOS:         {metrics.auc_degradation_pct:.1f}%")
    print(f"Brier Score OOS (Calibración):  {metrics.oos_brier:.4f} (Ideal < 0.23)")
    print(f"Win Rate Real OOS:             {metrics.oos_win_rate_actual * 100:.1f}%")
    print(f"Estado de Calibración:         {metrics.calibration.status}")
    print(f"Modelo Apto para Producción:   {'SÍ (VALIDADO)' if metrics.is_validated else 'NO (SIN CALIBRAR)'}")

    print("\nCurva de Calibración por Bins:")
    for i, (pred, emp, cnt) in enumerate(zip(metrics.calibration.bins_predicted, metrics.calibration.bins_empirical, metrics.calibration.bin_counts)):
        print(f"  Bin {i+1} [{pred*100:4.1f}% predicha] -> {emp*100:4.1f}% real empírica ({cnt} operaciones)")

    print("\nTop 10 Características más predictivas:")
    top_10 = sorted(metrics.feature_importances.items(), key=lambda x: x[1], reverse=True)[:10]
    for feat, imp in top_10:
        print(f"  - {feat:<30}: {imp * 100:.2f}%")

    # Registrar modelo campeón
    version_tag = f"v1.0.0-lgbm-{datetime.now().strftime('%Y%m%d')}"
    meta = model_registry.save_champion(
        pipeline=pipeline,
        version=version_tag,
        train_start=start_date,
        train_end=end_date,
        test_start=start_date,
        test_end=end_date,
    )

    print("\n" + "=" * 75)
    print(f"Modelo Campeón Registrado: {version_tag}")
    print(f"Ruta: data/models/champion.pkl")
    print("=" * 75)

if __name__ == "__main__":
    main()
