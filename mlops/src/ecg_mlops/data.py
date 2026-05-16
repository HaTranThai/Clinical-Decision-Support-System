"""Dataset preparation helpers shared by training and evaluation jobs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .paths import add_service_sources

add_service_sources()

from beat_extractor import extract_beat_segment  # noqa: E402
from mitbih_reader import load_record  # noqa: E402
from rr_morph_features import compute_rr4, morphology_features  # noqa: E402


SYMBOL_MAP = {
    "N": "N", "L": "N", "R": "N", "e": "N", "j": "N",
    "A": "A", "a": "A", "S": "A", "J": "A",
    "V": "V", "E": "V",
}

LABEL_TO_IDX = {"N": 0, "A": 1, "V": 2}
IDX_TO_LABEL = {idx: label for label, idx in LABEL_TO_IDX.items()}


@dataclass(frozen=True)
class ECGDatasetArrays:
    segments: np.ndarray
    rr4: np.ndarray
    m8: np.ndarray
    labels: np.ndarray
    meta: np.ndarray


def build_arrays(data_dir: Path, records: list[str]) -> ECGDatasetArrays:
    segments: list[np.ndarray] = []
    rr4_values: list[list[float]] = []
    m8_values: list[list[float]] = []
    labels: list[int] = []
    meta: list[tuple[str, float, str]] = []

    for record_name in records:
        record, annotation = load_record(str(data_dir), record_name)
        fs = int(record.fs)
        signal = record.p_signal
        channels_used = [0, 1] if signal.shape[1] >= 2 else [0]
        beat_samples = list(annotation.sample)
        beat_symbols = list(annotation.symbol)

        for idx, (sample, symbol) in enumerate(zip(beat_samples, beat_symbols)):
            mapped = SYMBOL_MAP.get(symbol)
            if mapped is None:
                continue

            segment = extract_beat_segment(signal, int(sample), fs, channels_used)
            if segment is None:
                continue

            segments.append(segment.astype(np.float32))
            rr4_values.append(compute_rr4(beat_samples, idx, fs))
            m8_values.append(morphology_features(segment))
            labels.append(LABEL_TO_IDX[mapped])
            meta.append((record_name, float(sample / fs), mapped))

    if not segments:
        raise RuntimeError(
            f"No usable beats found in {data_dir}. "
            "Copy MIT-BIH .dat/.hea/.atr files there or adjust params.yaml."
        )

    return ECGDatasetArrays(
        segments=np.stack(segments).astype(np.float32),
        rr4=np.asarray(rr4_values, dtype=np.float32),
        m8=np.asarray(m8_values, dtype=np.float32),
        labels=np.asarray(labels, dtype=np.int64),
        meta=np.asarray(meta, dtype=object),
    )


def build_arrays_for_records(data_dir: Path, records: list[str]) -> ECGDatasetArrays:
    """Same as build_arrays but explicit function for clarity."""
    return build_arrays(data_dir, records)


def save_arrays(arrays: ECGDatasetArrays, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        segments=arrays.segments,
        rr4=arrays.rr4,
        m8=arrays.m8,
        labels=arrays.labels,
        meta=arrays.meta,
        idx_to_label=np.asarray([IDX_TO_LABEL[i] for i in sorted(IDX_TO_LABEL)], dtype=object),
    )


def load_arrays(path: Path) -> ECGDatasetArrays:
    data = np.load(path, allow_pickle=True)
    return ECGDatasetArrays(
        segments=data["segments"],
        rr4=data["rr4"],
        m8=data["m8"],
        labels=data["labels"],
        meta=data["meta"],
    )
