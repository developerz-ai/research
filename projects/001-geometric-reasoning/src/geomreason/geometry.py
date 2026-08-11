"""Geometric descriptors of hidden-state structure.

These are **our operationalisation** of a term the source never defines. "Geometric density"
has no public definition (see ``library/sources/michels-sophontic-interview.md``), so we
measure several standard, established quantities and preregister all of them together. That
ordering matters: picking the metric after seeing which one correlates is how a null result
becomes a positive one.

None of these is "the" geometry of a model. They are complementary summaries of the
covariance structure of a layer's activations, and they disagree in informative ways.

Important limitation, stated up front: **all of these are correlational.** A metric that
tracks reasoning robustness may be a passenger rather than a cause. Distinguishing the two
requires intervention, which is a later experiment — see
``library/ideas/linear-representation-hypothesis.md`` on decodability vs use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import torch


@dataclass(frozen=True)
class LayerGeometry:
    """Geometric summary of one layer's activations over a set of inputs."""

    layer: int
    n_samples: int
    ambient_dim: int
    participation_ratio: float
    effective_rank: float
    intrinsic_dim_twonn: float
    anisotropy: float
    mean_norm: float

    def as_dict(self) -> dict:
        return asdict(self)


def participation_ratio(eigenvalues: np.ndarray) -> float:
    """(Σλ)² / Σλ² — the number of directions carrying meaningful variance.

    Equals the ambient dimension for an isotropic cloud and 1 for a cloud collapsed onto a
    single direction. Unlike a variance-threshold cutoff it needs no arbitrary threshold.
    """
    eig = np.clip(eigenvalues, 0, None)
    denom = float((eig**2).sum())
    return float(eig.sum() ** 2 / denom) if denom > 0 else 0.0


def effective_rank(eigenvalues: np.ndarray) -> float:
    """exp(Shannon entropy of the normalised spectrum) — Roy & Vetterli's effective rank.

    More sensitive than participation ratio to a long tail of small components, which is
    where superposition lives.
    """
    eig = np.clip(eigenvalues, 0, None)
    total = eig.sum()
    if total <= 0:
        return 0.0
    p = eig / total
    p = p[p > 1e-12]
    return float(np.exp(-(p * np.log(p)).sum()))


def intrinsic_dim_twonn(x: np.ndarray, discard_fraction: float = 0.1) -> float:
    """TwoNN intrinsic dimension estimator (Facco et al. 2017).

    Uses the ratio of the distances to the first and second nearest neighbours, so it
    measures the dimension of the *manifold* the points lie on rather than of the space they
    sit in. That is the quantity "geometric density" most plausibly refers to, though the
    source never says so.

    The top ``discard_fraction`` of ratios is dropped — the standard fix for the heavy tail
    that a handful of near-duplicate points otherwise produces.
    """
    n = x.shape[0]
    if n < 10:
        raise ValueError(f"TwoNN needs at least ~10 points, got {n}")

    # Chunked pairwise distances: n is a few thousand at most here, but the full matrix at
    # 4096 dims is still worth not materialising twice.
    dists = np.linalg.norm(x[:, None, :] - x[None, :, :], axis=-1)
    np.fill_diagonal(dists, np.inf)
    nearest = np.sort(dists, axis=1)[:, :2]

    r1, r2 = nearest[:, 0], nearest[:, 1]
    valid = (r1 > 1e-12) & (r2 > r1)
    if valid.sum() < 10:
        return float("nan")  # degenerate cloud (duplicates) — report, don't fabricate
    mu = np.sort(r2[valid] / r1[valid])

    keep = int(len(mu) * (1 - discard_fraction))
    mu = mu[:keep]
    # ML estimate: d = (N-1) / Σ log μ_i
    log_mu = np.log(mu)
    denom = log_mu.sum()
    return float(len(mu) / denom) if denom > 0 else float("nan")


def anisotropy(x: np.ndarray) -> float:
    """Mean pairwise cosine similarity of the raw (uncentred) vectors.

    High anisotropy — a well-documented property of transformer hidden states — means the
    cloud sits inside a narrow cone, so raw cosine similarity is a poor similarity measure.
    Recorded because it is a confound for every other metric here, not because it is
    interesting on its own.
    """
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = x / norms
    n = unit.shape[0]
    gram = unit @ unit.T
    off_diagonal = (gram.sum() - np.trace(gram)) / (n * (n - 1))
    return float(off_diagonal)


def describe_layer(activations: np.ndarray, layer: int) -> LayerGeometry:
    """Compute every descriptor for one layer's activation matrix (n_samples × dim)."""
    x = np.asarray(activations, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError(f"expected (n_samples, dim), got shape {x.shape}")

    centred = x - x.mean(axis=0, keepdims=True)
    # Eigenvalues of the covariance via SVD — cheaper and better conditioned than forming
    # the covariance matrix explicitly.
    singular = np.linalg.svd(centred, compute_uv=False)
    eigenvalues = (singular**2) / max(1, x.shape[0] - 1)

    return LayerGeometry(
        layer=layer,
        n_samples=int(x.shape[0]),
        ambient_dim=int(x.shape[1]),
        participation_ratio=round(participation_ratio(eigenvalues), 4),
        effective_rank=round(effective_rank(eigenvalues), 4),
        intrinsic_dim_twonn=round(intrinsic_dim_twonn(x), 4),
        anisotropy=round(anisotropy(x), 4),
        mean_norm=round(float(np.linalg.norm(x, axis=1).mean()), 4),
    )


@torch.no_grad()
def collect_hidden_states(
    loaded,  # LoadedModel — untyped to avoid a circular import
    prompts: list[str],
    batch_size: int = 8,
    max_samples: int = 512,
) -> dict[int, np.ndarray]:
    """Last-token hidden state per layer, for a set of prompts.

    The last token is used because that is the position the model would answer from, so it
    is the state that actually carries the decision. Mean-pooling instead would mix it with
    positions that do not.
    """
    tok = loaded.tokenizer
    device = loaded.device_info.device
    prompts = prompts[:max_samples]

    per_layer: dict[int, list[np.ndarray]] = {}
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        encoded = tok(batch, return_tensors="pt", padding=True, add_special_tokens=False)
        encoded = {k: v.to(device) for k, v in encoded.items()}
        out = loaded.model(**encoded, output_hidden_states=True)

        # Right padding: the last real token is at (length - 1), not at -1.
        lengths = encoded["attention_mask"].sum(dim=1) - 1
        for layer_idx, hidden in enumerate(out.hidden_states):
            picked = hidden[torch.arange(hidden.shape[0], device=device), lengths]
            per_layer.setdefault(layer_idx, []).append(picked.float().cpu().numpy())

    return {layer: np.concatenate(chunks, axis=0) for layer, chunks in per_layer.items()}
