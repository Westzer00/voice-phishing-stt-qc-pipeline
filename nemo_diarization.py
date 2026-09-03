from __future__ import annotations

import json
from pathlib import Path


def validate_wav(path: Path) -> float:
    import soundfile as sf

    info = sf.info(str(path))
    if info.samplerate != 16000:
        raise ValueError(f"{path.name}: expected 16 kHz, got {info.samplerate} Hz")
    if info.channels != 1:
        raise ValueError(f"{path.name}: expected mono audio, got {info.channels} channels")

    duration = info.frames / float(info.samplerate)
    if duration <= 0:
        raise ValueError(f"{path.name}: invalid duration")
    return duration


def write_manifest(wavs: list[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for wav in wavs:
            row = {
                "audio_filepath": str(wav.resolve()),
                "offset": 0.0,
                "duration": round(validate_wav(wav), 6),
                "label": "infer",
                "text": "-",
                "num_speakers": None,
                "rttm_filepath": None,
                "uem_filepath": None,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_config(base_config: Path, manifest: Path, output_dir: Path):
    """Load a NeMo telephonic diarization config and apply the production-safe overrides."""
    import torch
    from omegaconf import OmegaConf

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this NeMo diarization setup")

    cfg = OmegaConf.load(str(base_config))
    cfg.device = "cuda:0"
    cfg.num_workers = 0
    cfg.batch_size = 8
    cfg.diarizer.manifest_filepath = str(manifest.resolve())
    cfg.diarizer.out_dir = str(output_dir.resolve())
    cfg.diarizer.msdd_model.parameters.infer_batch_size = 8
    cfg.diarizer.oracle_vad = False
    cfg.diarizer.vad.external_vad_manifest = None
    cfg.diarizer.clustering.parameters.oracle_num_speakers = False
    cfg.diarizer.clustering.parameters.max_num_speakers = 8
    cfg.diarizer.msdd_model.parameters.seq_eval_mode = False
    return cfg


def parse_rttm(path: Path) -> list[dict]:
    segments = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 8:
            raise ValueError(f"Malformed RTTM at line {line_number}: {line}")
        if parts[0] != "SPEAKER":
            continue

        start = float(parts[3])
        duration = float(parts[4])
        segments.append(
            {
                "start": round(start, 3),
                "end": round(start + duration, 3),
                "speaker": parts[7],
            }
        )

    segments.sort(key=lambda item: (item["start"], item["end"], item["speaker"]))
    return segments


def run_diarization(base_config: Path, wav_dir: Path, output_dir: Path) -> None:
    from nemo.collections.asr.models.msdd_models import NeuralDiarizer

    wavs = sorted(wav_dir.glob("*.wav"))
    if not wavs:
        raise FileNotFoundError(f"No WAV files found in {wav_dir}")

    manifest = output_dir / "manifest.jsonl"
    write_manifest(wavs, manifest)
    cfg = load_config(base_config, manifest, output_dir)
    NeuralDiarizer(cfg=cfg).diarize()
