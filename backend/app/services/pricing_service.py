import csv
from pathlib import Path
from typing import Any

from sklearn.feature_extraction import DictVectorizer
from xgboost import XGBRegressor


class PricingService:
    """Train once from the bundled illustrative dataset and estimate task rewards."""

    categorical_features = ("region", "profession")
    numeric_features = ("demand", "supply")

    def __init__(self, training_examples: list[dict[str, Any]]) -> None:
        if len(training_examples) != 500:
            raise ValueError("The bundled synthetic pricing dataset must contain exactly 500 examples.")

        required = set((*self.categorical_features, *self.numeric_features, "price_points"))
        for index, example in enumerate(training_examples, start=1):
            missing = required.difference(example)
            if missing:
                raise ValueError(
                    f"Training example {index} is missing required fields: "
                    f"{', '.join(sorted(missing))}."
                )
            price = float(example["price_points"])
            if not 50 <= price <= 500:
                raise ValueError(f"Training example {index} price must be between 50 and 500 points.")

        self.training_example_count = len(training_examples)
        features = [self._encode_features(example) for example in training_examples]
        target = [float(example["price_points"]) for example in training_examples]
        self.vectorizer = DictVectorizer(sparse=True)
        training_matrix = self.vectorizer.fit_transform(features)
        self.model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=180,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            n_jobs=1,
            random_state=42,
        )
        self.model.fit(training_matrix, target)

    @staticmethod
    def _encode_features(example: dict[str, Any]) -> dict[str, float]:
        return {
            f"region={example['region']}": 1.0,
            f"profession={example['profession']}": 1.0,
            "demand": float(example["demand"]),
            "supply": float(example["supply"]),
        }

    @classmethod
    def from_csv(cls, csv_path: Path) -> "PricingService":
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            examples = [
                {
                    "region": row["region"],
                    "profession": row["profession"],
                    "demand": float(row["demand"]),
                    "supply": float(row["supply"]),
                    "price_points": float(row["price_points"]),
                }
                for row in csv.DictReader(source)
            ]
        return cls(examples)

    def estimate(self, requested_task: dict[str, Any]) -> float:
        features = self._encode_features(requested_task)
        request_matrix = self.vectorizer.transform([features])
        prediction = float(self.model.predict(request_matrix)[0])
        return round(min(500.0, max(50.0, prediction)), 2)


DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "pricing_training_data.csv"
pricing_service = PricingService.from_csv(DATASET_PATH)
