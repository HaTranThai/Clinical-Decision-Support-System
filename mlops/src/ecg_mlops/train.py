"""Train the ECG beat classifier and log the run to MLflow.

Expects pre-split train.npz and val.npz produced by prepare_data.py.
No data splitting is performed here — patient-level splits are fixed upstream.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import mlflow
import mlflow.pytorch
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, TensorDataset

from .config import load_config
from .data import IDX_TO_LABEL, load_arrays
from .paths import add_service_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

add_service_sources()

from model_def import CNN_RR4_Morph8  # noqa: E402


def _loader(
    segments: np.ndarray,
    rr4: np.ndarray,
    m8: np.ndarray,
    labels: np.ndarray,
    batch_size: int,
    shuffle: bool,
) -> DataLoader:
    dataset = TensorDataset(
        torch.tensor(segments, dtype=torch.float32),
        torch.tensor(rr4, dtype=torch.float32),
        torch.tensor(m8, dtype=torch.float32),
        torch.tensor(labels, dtype=torch.long),
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=0, pin_memory=False)


def _predict(
    model: CNN_RR4_Morph8, loader: DataLoader, device: torch.device
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    all_labels: list[np.ndarray] = []
    all_preds: list[np.ndarray] = []
    with torch.no_grad():
        for x, rr4, m8, y in loader:
            logits = model(x.to(device), rr4.to(device), m8.to(device))
            all_preds.append(torch.argmax(logits, dim=1).cpu().numpy())
            all_labels.append(y.numpy())
    return np.concatenate(all_labels), np.concatenate(all_preds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ECG arrhythmia classifier")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--train-data", default="data/processed/train.npz")
    parser.add_argument("--val-data", default="data/processed/val.npz")
    parser.add_argument("--output", default="artifacts/model/challenger.pt")
    args = parser.parse_args()

    cfg = load_config(args.params)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    logger.info(f"Loading train data from {args.train_data}")
    train_arrays = load_arrays(Path(args.train_data))
    logger.info(f"Loading val data from {args.val_data}")
    val_arrays = load_arrays(Path(args.val_data))

    train_loader = _loader(
        train_arrays.segments, train_arrays.rr4, train_arrays.m8, train_arrays.labels,
        cfg.batch_size, shuffle=True,
    )
    val_loader = _loader(
        val_arrays.segments, val_arrays.rr4, val_arrays.m8, val_arrays.labels,
        cfg.batch_size, shuffle=False,
    )

    in_ch = train_arrays.segments.shape[1]
    n_classes = len(IDX_TO_LABEL)
    model = CNN_RR4_Morph8(in_ch=in_ch, n_classes=n_classes).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay)
    criterion = nn.CrossEntropyLoss()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mlflow.set_experiment(cfg.experiment_name)

    best_val_f1 = -1.0
    best_state: dict | None = None
    best_val_metrics: dict = {}

    with mlflow.start_run(run_name="challenger-train") as run:
        run_id = run.info.run_id
        logger.info(f"MLflow run_id: {run_id}")

        mlflow.log_params({
            "train_records": ",".join(cfg.train_records),
            "val_records": ",".join(cfg.val_records),
            "n_train_beats": train_arrays.labels.shape[0],
            "n_val_beats": val_arrays.labels.shape[0],
            "epochs": cfg.epochs,
            "batch_size": cfg.batch_size,
            "learning_rate": cfg.learning_rate,
            "weight_decay": cfg.weight_decay,
            "in_ch": in_ch,
            "n_classes": n_classes,
        })

        for epoch in range(1, cfg.epochs + 1):
            model.train()
            losses: list[float] = []
            for x, rr4, m8, y in train_loader:
                optimizer.zero_grad(set_to_none=True)
                logits = model(x.to(device), rr4.to(device), m8.to(device))
                loss = criterion(logits, y.to(device))
                loss.backward()
                optimizer.step()
                losses.append(float(loss.item()))

            y_val, pred_val = _predict(model, val_loader, device)
            val_f1 = float(f1_score(y_val, pred_val, average="macro", zero_division=0))
            val_acc = float(accuracy_score(y_val, pred_val))
            train_loss = float(np.mean(losses))

            mlflow.log_metrics(
                {
                    "train_loss": train_loss,
                    "val_accuracy": val_acc,
                    "val_f1_macro": val_f1,
                },
                step=epoch,
            )
            logger.info(
                f"Epoch {epoch:3d}/{cfg.epochs} — loss={train_loss:.4f} "
                f"val_f1={val_f1:.4f} val_acc={val_acc:.4f}"
            )

            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}
                best_val_metrics = {"val_f1_macro": val_f1, "val_accuracy": val_acc}

        # Restore best weights
        if best_state is not None:
            model.load_state_dict(best_state)

        mlflow.log_metrics({
            "best_val_f1_macro": best_val_f1,
            **best_val_metrics,
        })

        # Log model artifact to MLflow
        mlflow.pytorch.log_model(model, artifact_path="model")

        # Save checkpoint with metadata
        checkpoint = {
            "model_state": model.state_dict(),
            "idx_to_label": IDX_TO_LABEL,
            "metrics": best_val_metrics,
            "mlflow_run_id": run_id,
            "in_ch": in_ch,
            "n_classes": n_classes,
        }
        torch.save(checkpoint, output_path)
        mlflow.log_artifact(str(output_path), artifact_path="checkpoint")
        logger.info(f"Saved challenger checkpoint to {output_path} (best val F1={best_val_f1:.4f})")


if __name__ == "__main__":
    main()
