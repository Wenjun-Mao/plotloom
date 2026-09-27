"""Lazy Qwen3-TTS inference adapter; fakeable without a GPU in tests."""

from __future__ import annotations

import gc
import random
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np

from .media import file_sha256


DESIGN_WEIGHTS_SHA256 = "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522"
BASE_WEIGHTS_SHA256 = "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c"


class ModelIntegrityError(RuntimeError):
    """The local weights no longer match the frozen reviewed checkpoint."""


class QwenEngine:
    def __init__(self, design_model_dir: Path, base_model_dir: Path):
        self.design_model_dir = design_model_dir
        self.base_model_dir = base_model_dir

    @staticmethod
    def _seed(value: int) -> None:
        import torch

        random.seed(value)
        np.random.seed(value)
        torch.manual_seed(value)
        torch.cuda.manual_seed_all(value)

    @contextmanager
    def design_session(self) -> Iterator["QwenDesignSession"]:
        with self._model(self.design_model_dir, DESIGN_WEIGHTS_SHA256) as model:
            session = QwenDesignSession(model, self._seed)
            try:
                yield session
            finally:
                session.model = None

    @contextmanager
    def clone_session(self) -> Iterator["QwenCloneSession"]:
        with self._model(self.base_model_dir, BASE_WEIGHTS_SHA256) as model:
            session = QwenCloneSession(model, self._seed)
            try:
                yield session
            finally:
                session.model = None

    @contextmanager
    def _model(self, path: Path, expected_hash: str):
        weights = path / "model.safetensors"
        if not weights.is_file():
            raise FileNotFoundError("model_unavailable")
        if file_sha256(weights) != expected_hash:
            raise ModelIntegrityError("model_weights_changed")
        import torch
        from qwen_tts import Qwen3TTSModel

        model = None
        try:
            model = Qwen3TTSModel.from_pretrained(
                str(path), device_map="cuda:0", dtype=torch.bfloat16,
                attn_implementation="sdpa",
            )
            yield model
        finally:
            del model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


class QwenDesignSession:
    def __init__(self, model, seed_fn):
        self.model = model
        self.seed_fn = seed_fn

    def generate(self, text: str, direction: str, seed: int) -> tuple[np.ndarray, int]:
        self.seed_fn(seed)
        waveforms, sample_rate = self.model.generate_voice_design(
            text=text, language="Chinese", instruct=direction, do_sample=True,
        )
        if len(waveforms) != 1:
            raise ValueError("invalid_model_audio")
        return waveforms[0], sample_rate


class QwenCloneSession:
    def __init__(self, model, seed_fn):
        self.model = model
        self.seed_fn = seed_fn

    def generate(self, text: str, reference: Path, reference_text: str, seed: int) -> tuple[np.ndarray, int]:
        self.seed_fn(seed)
        prompt = self.model.create_voice_clone_prompt(
            ref_audio=str(reference), ref_text=reference_text,
            x_vector_only_mode=False,
        )
        waveforms, sample_rate = self.model.generate_voice_clone(
            text=text, language="Chinese", voice_clone_prompt=prompt,
            do_sample=True,
        )
        if len(waveforms) != 1:
            raise ValueError("invalid_model_audio")
        return waveforms[0], sample_rate
