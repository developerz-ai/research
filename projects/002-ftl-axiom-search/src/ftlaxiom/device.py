"""Accelerator selection — the only module allowed to name a vendor backend.

Everything else calls :func:`pick_device` / :func:`autocast_dtype`. This is what keeps the
same experiment code running on NVIDIA, AMD, and CPU.

The trap this module exists to close: ``torch.cuda.is_available()`` returns ``True`` on
AMD/ROCm builds of PyTorch. It is a *"is there an accelerator"* test, not a vendor test.
Branching on it to pick CUDA-only code paths puts CUDA code on an AMD card.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

import torch

Backend = Literal["cuda", "rocm", "xpu", "cpu"]


@dataclass(frozen=True)
class DeviceInfo:
    """What we are actually running on, resolved once and reported everywhere."""

    backend: Backend
    device: torch.device
    name: str
    total_memory_gb: float | None
    supports_bf16: bool
    torch_version: str
    build: str  # the accelerator version torch was compiled against
    notes: list[str] = field(default_factory=list)

    @property
    def is_accelerated(self) -> bool:
        return self.backend != "cpu"

    def as_dict(self) -> dict:
        return {
            "backend": self.backend,
            "device": str(self.device),
            "name": self.name,
            "total_memory_gb": self.total_memory_gb,
            "supports_bf16": self.supports_bf16,
            "torch_version": self.torch_version,
            "build": self.build,
        }


def _detect_backend() -> Backend:
    """Resolve the backend, honouring RESEARCH_DEVICE if set."""
    forced = os.environ.get("RESEARCH_DEVICE", "auto").strip().lower()
    if forced in ("cpu", "cuda", "rocm", "xpu"):
        if forced != "cpu" and not _backend_available(forced):  # type: ignore[arg-type]
            raise RuntimeError(
                f"RESEARCH_DEVICE={forced} but that backend is not available in this "
                f"torch build ({torch.__version__}). Unset it or install the right wheel."
            )
        return forced  # type: ignore[return-value]
    if forced not in ("auto", ""):
        raise ValueError(f"RESEARCH_DEVICE must be auto|cpu|cuda|rocm|xpu, got {forced!r}")

    if torch.cuda.is_available():
        # torch.version.hip is set only on ROCm builds; torch.cuda.* is the ROCm API too.
        return "rocm" if getattr(torch.version, "hip", None) else "cuda"
    if hasattr(torch, "xpu") and torch.xpu.is_available():  # Intel
        return "xpu"
    return "cpu"


def _backend_available(backend: Backend) -> bool:
    if backend == "cuda":
        return torch.cuda.is_available() and not getattr(torch.version, "hip", None)
    if backend == "rocm":
        return torch.cuda.is_available() and bool(getattr(torch.version, "hip", None))
    if backend == "xpu":
        return hasattr(torch, "xpu") and torch.xpu.is_available()
    return True


def _supports_bf16(backend: Backend) -> bool:
    """bf16 is silently catastrophic where unsupported — check, never assume."""
    if backend in ("cuda", "rocm"):
        try:
            return torch.cuda.is_bf16_supported()
        except Exception:
            return False
    # Intel XPU supports bf16; CPU bf16 exists but is usually slower than fp32 without AMX,
    # so it is not worth taking.
    return backend == "xpu"


def get_device_info() -> DeviceInfo:
    """Resolve the accelerator once and describe it fully."""
    backend = _detect_backend()
    notes: list[str] = []

    if backend in ("cuda", "rocm"):
        idx = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(idx)
        name = props.name
        total = props.total_memory / 1e9
        device = torch.device(f"cuda:{idx}")  # ROCm also uses the "cuda" device string
        build = (
            f"rocm {torch.version.hip}"
            if backend == "rocm"
            else f"cuda {torch.version.cuda}"
        )
        if backend == "rocm":
            notes.append(
                "ROCm build: device strings are still 'cuda'. Do not treat that as NVIDIA."
            )
    elif backend == "xpu":
        device = torch.device("xpu")
        name = torch.xpu.get_device_name(0)
        total = None
        build = "xpu"
    else:
        device = torch.device("cpu")
        name = "cpu"
        total = None
        build = "cpu"
        notes.append(
            "No accelerator. Every experiment must still run here — use a small --limit."
        )

    return DeviceInfo(
        backend=backend,
        device=device,
        name=name,
        total_memory_gb=round(total, 1) if total else None,
        supports_bf16=_supports_bf16(backend),
        torch_version=torch.__version__,
        build=build,
        notes=notes,
    )


def pick_device() -> torch.device:
    """The device every experiment should use. Never hardcode a device string."""
    return get_device_info().device


def autocast_dtype(info: DeviceInfo | None = None) -> torch.dtype:
    """Best inference dtype for this device.

    bf16 where genuinely supported (Ampere+, MI200+), fp32 everywhere else. fp16 is
    deliberately not chosen automatically — its narrow range makes it easy to produce
    silent NaNs in log-likelihood scoring, which is exactly what we measure.
    """
    info = info or get_device_info()
    return torch.bfloat16 if info.supports_bf16 else torch.float32


def enable_fast_matmul() -> None:
    """Opt into TF32 on hardware that has it. Harmless elsewhere."""
    try:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
    except Exception:
        pass


def seed_everything(seed: int) -> None:
    """Seed every RNG we touch. Seeds come from config, never from source."""
    import random

    import numpy as np

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
