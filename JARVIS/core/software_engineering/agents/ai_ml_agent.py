"""
JARVIS AI & ML Agent — SE Layer.

Generates Machine Learning pipeline code, dataset configurations,
training/evaluation scripts, and model inference API endpoints:
  - Scikit-learn classification & regression models
  - PyTorch neural network training scripts
  - Dataset ingestion & preprocessing pipelines
  - Model evaluation reports
  - Fast-API inference endpoints
"""

from __future__ import annotations

import os
from typing import Any

from JARVIS.core.software_engineering.agents.architect_agent import ArchitectureSpec
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("ai_ml_agent")


class AIMLAgent:
    """Generates AI & ML pipeline code and model inference APIs."""

    def generate(self, spec: ArchitectureSpec) -> dict[str, Any]:
        if not spec.ml_stack:
            return {"success": True, "files": [], "message": "No ML stack required."}

        logger.info("AIMLAgent generating %s pipeline for %s", spec.ml_stack, spec.project_name)
        ml_dir = os.path.join(spec.workspace_path, "ml")
        files_written: list[str] = []

        # Generate dataset pipeline
        files_written.append(self._write(os.path.join(ml_dir, "src"), "dataset.py", self._dataset_pipeline()))

        # Generate model architecture
        files_written.append(self._write(os.path.join(ml_dir, "src"), "model.py", self._model_architecture(spec)))

        # Generate training script
        files_written.append(self._write(os.path.join(ml_dir, "src"), "train.py", self._train_script(spec)))

        # Generate evaluation script
        files_written.append(self._write(os.path.join(ml_dir, "src"), "evaluate.py", self._evaluate_script(spec)))

        # Generate FastAPI Inference Endpoint
        files_written.append(self._write(os.path.join(ml_dir, "src"), "inference_api.py", self._inference_api(spec)))

        # Generate requirements.txt
        files_written.append(self._write(ml_dir, "requirements.txt", self._requirements(spec)))

        # Generate README.md for ML section
        files_written.append(self._write(ml_dir, "README.md", self._ml_readme(spec)))

        return {
            "success": True,
            "files": files_written,
            "ml_stack": spec.ml_stack,
            "message": f"Generated {len(files_written)} ML pipeline and inference files.",
        }

    def _dataset_pipeline(self) -> str:
        return """\"\"\"Dataset Ingestion & Preprocessing Pipeline\"\"\"
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def load_and_preprocess_data(filepath: str, target_column: str, test_size: float = 0.2, random_state: int = 42):
    \"\"\"Load dataset, scale numeric features, and perform train-test split.\"\"\"
    print(f"Loading data from {filepath}...")
    df = pd.read_csv(filepath)

    X = df.drop(columns=[target_column])
    y = df[target_column]

    # Handle missing values
    X = X.fillna(X.mean(numeric_only=True))

    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler
"""

    def _model_architecture(self, spec: ArchitectureSpec) -> str:
        stack = spec.ml_stack.lower()
        if "pytorch" in stack:
            return """\"\"\"PyTorch Neural Network Architecture\"\"\"
import torch
import torch.nn as nn


class SimpleNeuralNetwork(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 1):
        super(SimpleNeuralNetwork, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim)
        )

    def forward(self, x):
        return self.network(x)
"""
        # Default scikit-learn random forest or similar wrapper
        return """\"\"\"Scikit-Learn Model Architectures\"\"\"
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression


def get_model(model_type: str = "random_forest", **kwargs):
    \"\"\"Factory to retrieve configured ML models.\"\"\"
    if model_type == "random_forest":
        return RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, **kwargs)
    elif model_type == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=42, **kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
"""

    def _train_script(self, spec: ArchitectureSpec) -> str:
        stack = spec.ml_stack.lower()
        if "pytorch" in stack:
            return """\"\"\"PyTorch Model Training Utility\"\"\"
import torch
import torch.nn as nn
import torch.optim as optim
from model import SimpleNeuralNetwork
from dataset import load_and_preprocess_data


def train_model(data_path: str, target: str, epochs: int = 50, batch_size: int = 32):
    X_train, X_test, y_train, y_test, scaler = load_and_preprocess_data(data_path, target)

    # Convert to Tensors
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.FloatTensor(y_train.values).unsqueeze(1)

    model = SimpleNeuralNetwork(input_dim=X_train.shape[1])
    criterion = nn.BSELoss()  # Replace with appropriate loss depending on task
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    print("Starting PyTorch training loop...")
    for epoch in range(epochs):
        model.train()
        permutation = torch.randperm(X_train_t.size()[0])
        for i in range(0, X_train_t.size()[0], batch_size):
            indices = permutation[i:i+batch_size]
            batch_x, batch_y = X_train_t[indices], y_train_t[indices]

            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs} | Loss: {loss.item():.4f}")

    # Save components
    torch.save(model.state_dict(), "best_model.pth")
    import joblib
    joblib.dump(scaler, "scaler.joblib")
    print("Training successfully complete. Saved model to best_model.pth")
"""
        return """\"\"\"Model Training Script\"\"\"
import joblib
from dataset import load_and_preprocess_data
from model import get_model


def train_and_save(data_path: str, target: str, model_type: str = "random_forest"):
    X_train, X_test, y_train, y_test, scaler = load_and_preprocess_data(data_path, target)

    model = get_model(model_type)
    print(f"Training {model_type}...")
    model.fit(X_train, y_train)

    # Evaluate validation score
    score = model.score(X_test, y_test)
    print(f"Validation Score: {score:.4f}")

    # Persist model and preprocessing scaler
    joblib.dump(model, "best_model.joblib")
    joblib.dump(scaler, "scaler.joblib")
    print("Training successfully complete. Model artifacts saved.")
"""

    def _evaluate_script(self, spec: ArchitectureSpec) -> str:
        return """\"\"\"Model Evaluation Suite\"\"\"
import joblib
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from dataset import load_and_preprocess_data


def evaluate_saved_model(data_path: str, target: str):
    X_train, X_test, y_train, y_test, _ = load_and_preprocess_data(data_path, target)

    # Load artifacts
    model = joblib.load("best_model.joblib")

    # Generate predictions
    y_pred = model.predict(X_test)

    print("=== MODEL EVALUATION REPORT ===")
    print(f"Accuracy Score: {accuracy_score(y_test, y_pred):.4f}")
    print("\\nClassification Report:")
    print(classification_report(y_test, y_pred))
    print("\\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
"""

    def _inference_api(self, spec: ArchitectureSpec) -> str:
        return """\"\"\"Model Inference API Endpoints\"\"\"
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Model Inference API", version="1.0.0")

# Load model and scaler globally
try:
    model = joblib.load("best_model.joblib")
    scaler = joblib.load("scaler.joblib")
except Exception:
    model = None
    scaler = None
    print("WARNING: Model and scaler artifacts not found. Please train the model first.")


class PredictionInput(BaseModel):
    features: List[float]


class PredictionOutput(BaseModel):
    prediction: int
    probabilities: List[float] = []


@app.get("/health")
def health():
    return {"status": "model_api_active", "model_loaded": model is not None}


@app.post("/predict", response_model=PredictionOutput)
def predict(payload: PredictionInput):
    if model is None or scaler is None:
        raise HTTPException(status_code=503, detail="Model artifacts are not loaded.")

    try:
        # Reshape and scale input features
        input_data = np.array(payload.features).reshape(1, -1)
        scaled_data = scaler.transform(input_data)

        # Generate prediction
        prediction = int(model.predict(scaled_data)[0])
        probabilities = []

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(scaled_data)[0].tolist()

        return PredictionOutput(prediction=prediction, probabilities=probabilities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference execution fault: {e}")
"""

    def _requirements(self, spec: ArchitectureSpec) -> str:
        stack = spec.ml_stack.lower()
        base = ["pandas", "numpy", "scikit-learn", "joblib", "fastapi", "uvicorn", "pydantic"]
        if "pytorch" in stack:
            base += ["torch", "torchvision"]
        elif "tensorflow" in stack:
            base += ["tensorflow"]
        return "\n".join(base)

    def _ml_readme(self, spec: ArchitectureSpec) -> str:
        return f"""# AI & ML Pipeline — {spec.project_name}

**Stack:** {spec.ml_stack}

This folder contains the dataset preprocessing, training scripts, evaluation suite, and inference API.

## Project Structure
- `src/dataset.py`: Raw dataset loading, cleaning, scaling, and splitting.
- `src/model.py`: Model architecture specifications.
- `src/train.py`: Model training pipeline.
- `src/evaluate.py`: Quality validation, confusion matrix, precision/recall metrics.
- `src/inference_api.py`: FastAPI model wrapper to serve inferences.

## Running Locally

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Run training:
   ```python
   # Call train_and_save() from python REPL
   ```

3. Spin up inference API:
   ```bash
   uvicorn src.inference_api:app --host 0.0.0.0 --port 8080
   ```
"""

    def _write(self, directory: str, filename: str, content: str) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            return path
        except Exception as e:
            logger.error("AIMLAgent write error: %s", e)
            return path
