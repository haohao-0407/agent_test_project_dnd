from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv


class EmbeddingModel(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


@dataclass(frozen=True, slots=True)
class HashEmbeddingModel:
    """Deterministic lightweight embedding for tests and smoke runs."""

    dimensions: int = 32

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0 for _ in range(self.dimensions)]
        tokens = _tokens(text)
        if not tokens:
            tokens = [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index, byte in enumerate(digest):
                vector[index % self.dimensions] += (byte / 255.0) - 0.5
        return _normalize(vector)


class SentenceTransformerEmbeddingModel:
    """Local sentence-transformers embedding wrapper."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        *,
        cache_folder: str | Path | None = None,
    ) -> None:
        cache_path = Path(cache_folder) if cache_folder else _default_model_cache()
        cache_path.mkdir(parents=True, exist_ok=True)
        _configure_huggingface_cache(cache_path)

        from sentence_transformers import SentenceTransformer

        self.model = _load_sentence_transformer(
            SentenceTransformer,
            model_name,
            cache_path,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def _tokens(text: str) -> list[str]:
    normalized = text.lower().strip()
    words = [word for word in normalized.split() if word]
    if words:
        return words
    return [char for char in normalized if not char.isspace()]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _default_model_cache() -> Path:
    return Path(__file__).resolve().parents[2] / ".cache" / "sentence_transformers"


def _configure_huggingface_cache(model_cache: Path) -> None:
    load_dotenv()
    hf_home = model_cache.parent / "huggingface"
    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HF_HUB_CACHE", str(hf_home / "hub"))
    os.environ.setdefault("HF_XET_CACHE", str(hf_home / "xet"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_home / "transformers"))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


def _load_sentence_transformer(
    sentence_transformer_cls,
    model_name: str,
    cache_path: Path,
):
    try:
        return sentence_transformer_cls(
            model_name,
            cache_folder=str(cache_path),
            local_files_only=True,
        )
    except Exception as local_error:
        try:
            return sentence_transformer_cls(
                model_name,
                cache_folder=str(cache_path),
                local_files_only=False,
            )
        except Exception:
            raise local_error
