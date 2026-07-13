"""ML modeli: "yükseliş öncesi" olasılığını öğrenir.

Gradient Boosting (histogram tabanlı) sınıflandırıcı kullanır. Girdi,
features.py'nin ürettiği özellik matrisi; hedef, labeling.py'nin ürettiği
ikili "yükseldi mi?" etiketi.

Model, hangi özelliklerin yükselişten önce önemli olduğunu (feature
importance) da raporlar — yani ajanın "neden yükseldiğini öğrenmesi" burada
somutlaşır.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance

from .features import FEATURE_COLUMNS


@dataclass
class TrainReport:
    n_samples: int
    n_positive: int
    positive_rate: float
    train_auc: float
    holdout_auc: Optional[float]
    top_features: list = field(default_factory=list)  # [(isim, önem), ...]

    def summary(self) -> str:
        lines = [
            f"Örnek sayısı      : {self.n_samples}",
            f"Pozitif (yükseldi): {self.n_positive} (%{self.positive_rate*100:.1f})",
            f"Eğitim AUC        : {self.train_auc:.3f}",
        ]
        if self.holdout_auc is not None:
            lines.append(f"Doğrulama AUC     : {self.holdout_auc:.3f}")
        lines.append("En önemli belirtiler (yükseliş sebepleri):")
        for name, imp in self.top_features[:8]:
            lines.append(f"    {name:<22} {imp:+.4f}")
        return "\n".join(lines)


class SignalModel:
    """Özellik matrisinden yükseliş olasılığı öğrenen model sarmalayıcı."""

    def __init__(self, params: Optional[dict] = None):
        default = dict(
            learning_rate=0.06,
            max_depth=4,
            max_iter=300,
            l2_regularization=1.0,
            min_samples_leaf=40,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=42,
        )
        if params:
            default.update(params)
        self.params = default
        self.clf = HistGradientBoostingClassifier(**default)
        self.feature_columns = list(FEATURE_COLUMNS)
        self.is_fitted = False
        self.report: Optional[TrainReport] = None

    # ------------------------------------------------------------------ #
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        holdout_frac: float = 0.2,
        compute_importance: bool = True,
    ) -> TrainReport:
        """Modeli eğitir. X: özellik matrisi, y: 0/1 etiket.

        Zaman serisi olduğundan holdout kronolojik olarak sondan ayrılır
        (rastgele değil) — böylece geleceği görmeden değerlendiririz.
        """
        from sklearn.metrics import roc_auc_score

        X = X[self.feature_columns].copy()
        mask = y.notna()
        X, y = X[mask], y[mask].astype(int)

        if len(X) < 100:
            raise ValueError(f"Eğitim için yetersiz veri: {len(X)} satır (min 100)")

        n_hold = int(len(X) * holdout_frac)
        if n_hold > 20 and y.iloc[:-n_hold].nunique() > 1:
            X_tr, X_ho = X.iloc[:-n_hold], X.iloc[-n_hold:]
            y_tr, y_ho = y.iloc[:-n_hold], y.iloc[-n_hold:]
        else:
            X_tr, y_tr, X_ho, y_ho = X, y, None, None

        self.clf.fit(X_tr, y_tr)
        self.is_fitted = True

        train_auc = _safe_auc(y_tr, self.clf.predict_proba(X_tr)[:, 1])
        holdout_auc = None
        if X_ho is not None and y_ho.nunique() > 1:
            holdout_auc = _safe_auc(y_ho, self.clf.predict_proba(X_ho)[:, 1])

        top_features = []
        if compute_importance:
            top_features = self._importance(X_tr, y_tr)

        self.report = TrainReport(
            n_samples=len(X),
            n_positive=int(y.sum()),
            positive_rate=float(y.mean()),
            train_auc=train_auc,
            holdout_auc=holdout_auc,
            top_features=top_features,
        )
        return self.report

    def _importance(self, X: pd.DataFrame, y: pd.Series) -> list:
        """Permütasyon önemi — hangi belirti tahmini ne kadar taşıyor."""
        try:
            res = permutation_importance(
                self.clf, X, y, n_repeats=5, random_state=42, scoring="roc_auc"
            )
            pairs = sorted(
                zip(self.feature_columns, res.importances_mean),
                key=lambda p: abs(p[1]),
                reverse=True,
            )
            return [(n, float(v)) for n, v in pairs]
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Her satır için yükseliş olasılığı (0..1)."""
        if not self.is_fitted:
            raise RuntimeError("Model eğitilmedi. Önce train() çağır.")
        X = X[self.feature_columns]
        return self.clf.predict_proba(X)[:, 1]

    def predict_one(self, row: pd.Series) -> float:
        X = pd.DataFrame([row])[self.feature_columns]
        return float(self.clf.predict_proba(X)[:, 1][0])

    # ------------------------------------------------------------------ #
    def save(self, path: str | Path) -> None:
        import joblib

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "clf": self.clf,
                "feature_columns": self.feature_columns,
                "params": self.params,
                "report": self.report.__dict__ if self.report else None,
            },
            path,
        )

    @classmethod
    def load(cls, path: str | Path) -> "SignalModel":
        import joblib

        blob = joblib.load(path)
        obj = cls(params=blob.get("params"))
        obj.clf = blob["clf"]
        obj.feature_columns = blob["feature_columns"]
        obj.is_fitted = True
        rep = blob.get("report")
        if rep:
            obj.report = TrainReport(**rep)
        return obj


def _safe_auc(y_true, y_score) -> float:
    from sklearn.metrics import roc_auc_score

    try:
        if len(np.unique(y_true)) < 2:
            return float("nan")
        return float(roc_auc_score(y_true, y_score))
    except Exception:
        return float("nan")
