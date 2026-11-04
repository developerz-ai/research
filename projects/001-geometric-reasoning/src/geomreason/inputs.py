"""Identical-input bookkeeping for matched runs.

E002's premise is that the hidden-state geometry and the flip rate were measured on the
*same* prompts. The committed records break that premise silently: the flip-rate runs
(``E001*``) generated 100 pairs per family (1200 items) while the geometry runs
(``E002-geom-*``) generated 24 per family truncated to 288 prompts. Because
:func:`geomreason.items.generate` draws ONE ``random.Random(seed)`` stream sequentially
across families in insertion order, two populations generated at different
``n_per_family`` coincide **only in their first family** — 48 of 288 prompts here.
Nothing in the records flagged this: ``config["families"]`` was stored sorted while
generation ran in insertion order, geometry recorded no prompt list at all
(``items=[]``), and no digest existed to compare.

This module makes the premise checkable instead of assumed:

* :func:`population_digest` — a short fingerprint of an ordered prompt list.
* :func:`from_behavior_record` / :func:`from_geometry_record` — rebuild a run's prompt
  population from its record, verifying the reconstruction wherever the record allows it.
* :func:`compare` — overlap between two populations, attributed by family.

Pure stdlib plus :mod:`geomreason.items` (no torch): population checks must run anywhere,
including CPU-only CI.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .items import FAMILIES, flatten, generate


def population_digest(prompts: list[str]) -> str:
    """First 16 hex digits of the SHA-256 of the ordered prompt list.

    Order-sensitive by design: a population is a *sequence* of prompts, and truncation
    changes the digest even when the underlying set does not.
    """
    payload = json.dumps(list(prompts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def generation_order(families: list[str] | None) -> list[str]:
    """Families in the order :func:`geomreason.items.generate` actually drew them.

    The trap this resolves: the CLI stores ``config["families"]`` **sorted**, but every
    committed run called ``generate(families=None)`` — insertion order (comparison,
    transitive, negation, arithmetic, role_swap, conditional). Regenerating from the
    stored sorted list would draw the RNG stream in a different order and produce a
    different population from the first family onward. Whenever the recorded set is the
    full set, the executed call was the default, so the insertion order is the right one.
    """
    if families is None or set(families) == set(FAMILIES):
        return list(FAMILIES)
    return list(families)


@dataclass(frozen=True)
class ItemPopulation:
    """The exact prompt population behind one run record, and the config that drew it.

    ``families`` is the **generation order** (see :func:`generation_order`);
    ``max_samples`` is the truncation applied after generation, ``0`` = none;
    ``digest`` is :func:`population_digest` over :attr:`prompts`.
    """

    families: list[str]
    n_per_family: int
    seed: int
    max_samples: int
    prompts: list[str]
    digest: str

    def labels(self) -> list[tuple[str, str]]:
        """(pair_id, family) per prompt, regenerated from this population's config.

        Deterministic — the same (order, n_per_family, seed) always draws the same
        stream — so the labels align with :attr:`prompts`, truncation included.
        """
        items = flatten(
            generate(n_per_family=self.n_per_family, seed=self.seed, families=self.families)
        )
        labels = [(i.pair_id, i.family) for i in items]
        return labels[: self.max_samples] if self.max_samples > 0 else labels


def from_config(
    n_per_family: int,
    seed: int,
    families: list[str] | None = None,
    max_samples: int = 0,
) -> ItemPopulation:
    """Build the population a config describes, resolving the stored-families trap."""
    order = generation_order(families)
    items = flatten(generate(n_per_family=n_per_family, seed=seed, families=order))
    prompts = [i.prompt for i in items]
    if max_samples > 0:
        prompts = prompts[:max_samples]
    return ItemPopulation(
        families=order,
        n_per_family=n_per_family,
        seed=seed,
        max_samples=max_samples,
        prompts=prompts,
        digest=population_digest(prompts),
    )


def population_block(
    *,
    n_per_family: int,
    seed: int,
    families: list[str],
    max_samples: int,
    prompts: list[str],
) -> dict:
    """The ``input_population`` config block a run record stores: what was shown.

    ``families`` is stored sorted for key stability across records; the generation order
    is recovered by :func:`generation_order`. ``prompt_digest`` fingerprints the prompts
    actually shown to the model, i.e. after any truncation.
    """
    return {
        "families": sorted(families),
        "n_per_family": n_per_family,
        "seed": seed,
        "max_samples": max_samples,
        "n_prompts": len(prompts),
        "prompt_digest": population_digest(prompts),
    }


def _from_block(block: dict) -> ItemPopulation:
    return from_config(
        n_per_family=block["n_per_family"],
        seed=block["seed"],
        families=block.get("families"),
        max_samples=block.get("max_samples", 0),
    )


def from_behavior_record(record: dict) -> ItemPopulation:
    """Rebuild the prompt population of a flip-rate (behavior) record.

    Behavior records carry the prompt of every scored item, so the reconstruction is
    *verified*: a config that does not reproduce the stored per-item prompts raises
    rather than letting a population comparison run on a guess.
    """
    cfg = record.get("config", {})
    stored = [item["prompt"] for item in record.get("items", [])]
    if not stored:
        raise ValueError("not a behavior record: no per-item prompts under 'items'")

    block = cfg.get("input_population")
    if block is not None:
        pop = _from_block(block)
    else:
        n_per_family = cfg.get("n_per_family")
        if n_per_family is None:
            raise ValueError("behavior record config has no n_per_family — cannot rebuild")
        pop = from_config(
            n_per_family=n_per_family,
            seed=record["seed"],
            families=cfg.get("families"),
            max_samples=cfg.get("max_samples", 0),
        )

    if pop.prompts != stored:
        raise ValueError(
            "record config does not reproduce its stored per-item prompts — the population "
            "cannot be reconstructed from this record; do not compare it"
        )
    recorded_digest = (block or cfg).get("prompt_digest")
    if recorded_digest is not None and recorded_digest != pop.digest:
        raise ValueError(
            f"prompt_digest mismatch: record says {recorded_digest}, "
            f"reconstruction gives {pop.digest}"
        )
    return pop


def from_geometry_record(record: dict) -> ItemPopulation:
    """Rebuild the prompt population of a hidden-state geometry record.

    Geometry records carry no prompts (``items=[]``), so the population is reconstructed
    from config alone. Legacy records (no ``input_population`` block) name no ``families``
    key at all — the executed call was the default, full family set — and carry no digest,
    so their reconstruction is plausible rather than verified. New records carry the
    block and are digest-checked here.
    """
    cfg = record.get("config", {})
    block = cfg.get("input_population")
    if block is not None:
        pop = _from_block(block)
        if pop.digest != block.get("prompt_digest"):
            raise ValueError(
                f"input_population.prompt_digest mismatch: record says "
                f"{block.get('prompt_digest')}, reconstruction gives {pop.digest}"
            )
        return pop

    n_per_family = cfg.get("n_per_family")
    if n_per_family is None:
        raise ValueError("geometry record config has no n_per_family — cannot rebuild")
    return from_config(
        n_per_family=n_per_family,
        seed=record["seed"],
        families=cfg.get("families"),
        max_samples=cfg.get("max_samples", 0),
    )


@dataclass(frozen=True)
class PopulationComparison:
    """Position-aligned agreement between two populations' ordered prompt lists.

    ``shared`` is the element-wise common prefix: the prompts both runs showed, at the
    same position of the same seeded stream, with ``a``'s labelling attached. This is
    deliberately stricter than set overlap — a low-entropy family (negation has only 128
    distinct prompts) can produce the same string at two independent stream positions,
    and a chance collision is not a matched input.

    ``common_prefix`` is the length of that agreement in prompts; ``n_only_a`` /
    ``n_only_b`` count what each side showed beyond it.
    """

    a: ItemPopulation
    b: ItemPopulation
    shared: list[str]
    shared_pair_ids: list[str]
    shared_families: dict[str, int]
    n_only_a: int
    n_only_b: int
    common_prefix: int

    @property
    def identical(self) -> bool:
        """Same prompts, same order — the identical-input premise holds."""
        return self.a.prompts == self.b.prompts

    @property
    def n_shared(self) -> int:
        return len(self.shared)

    @property
    def confined_to_first_family(self) -> bool:
        """Every shared prompt comes from the first family drawn.

        The signature of one RNG stream drawn family by family: a shorter run shares its
        first family with a longer one and diverges at the second — the executed
        E001/E002 mismatch.
        """
        return set(self.shared_families) <= {self.a.families[0]}


def compare(a: ItemPopulation, b: ItemPopulation) -> PopulationComparison:
    """Compare two populations position by position: how far they agree, and in what.

    "Shared" means position-aligned agreement — the same prompt at the same place in the
    same seeded stream. Chance template collisions at independent stream positions are
    not counted; they are coincidences, not matched inputs.
    """
    common_prefix = 0
    for x, y in zip(a.prompts, b.prompts, strict=False):
        if x != y:
            break
        common_prefix += 1

    prefix_labels = a.labels()[:common_prefix]
    shared_families: dict[str, int] = {}
    for _, family in prefix_labels:
        shared_families[family] = shared_families.get(family, 0) + 1

    return PopulationComparison(
        a=a,
        b=b,
        shared=a.prompts[:common_prefix],
        shared_pair_ids=[pair_id for pair_id, _ in prefix_labels],
        shared_families=shared_families,
        n_only_a=len(a.prompts) - common_prefix,
        n_only_b=len(b.prompts) - common_prefix,
        common_prefix=common_prefix,
    )
