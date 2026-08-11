"""Paired-perturbation item generation.

Each :class:`Pair` is two items that differ by exactly one load-bearing fact, share the same
two answer options, and have *opposite* correct answers. A model that reasons answers both
correctly; a model matching surface patterns answers the same option twice and scores at
chance on the pair.

Design rules, each closing a specific way this measurement gets faked (see
``library/ideas/flip-rate-evaluation.md``):

* **Identical option strings across the pair.** Only which one is correct changes. This
  removes option-string, length, and frequency effects by construction rather than by
  statistical correction.
* **Minimal surface edit.** One word or number moves. The more the surface changes, the more
  the score reflects some other shortcut.
* **Balanced correct answers, within each variant.** Each family template fixes which option
  is correct for its canonical member, so without intervention *every* canonical item in a
  family would share the same correct index — and a model with a per-family option bias
  would post inflated canonical accuracy. Option order is therefore randomly swapped per
  pair (both members together), making the correct index ~50/50 within each variant while
  keeping the options identical across the pair.
* **Generated fresh from a seed, never published.** Contamination cannot help; recall of a
  memorised answer actively costs the model a point on the perturbed member.
* **Uniquely determined answers.** No item may be ambiguous or require world knowledge
  beyond the prompt. Under-determined perturbations (e.g. denying the antecedent) are the
  easiest mistake to make here and are deliberately excluded.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import asdict, dataclass

NAMES = [
    "Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry",
    "Irene", "Jack", "Karen", "Liam", "Maya", "Noah", "Olivia", "Peter",
]

OBJECTS = ["book", "key", "cup", "lamp", "coin", "map", "pen", "box"]


@dataclass(frozen=True)
class Item:
    """One prompt with two candidate continuations, exactly one of which is correct."""

    prompt: str
    options: tuple[str, str]
    correct_index: int
    family: str
    variant: str  # "canonical" | "perturbed"
    pair_id: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Pair:
    canonical: Item
    perturbed: Item

    def validate(self) -> None:
        """Structural guarantees. A generator bug here silently changes what we measure."""
        c, p = self.canonical, self.perturbed
        if c.options != p.options:
            raise ValueError(f"{c.pair_id}: options must be identical across the pair")
        if c.correct_index == p.correct_index:
            raise ValueError(
                f"{c.pair_id}: perturbation did not flip the answer — the edited fact was "
                "not load-bearing"
            )
        if c.prompt == p.prompt:
            raise ValueError(f"{c.pair_id}: prompts identical")
        if len(set(c.options)) != 2:
            raise ValueError(f"{c.pair_id}: options must be distinct")


# ─────────────────────────────────────────────────────────────────── families
#
# Each family takes an RNG and an index, and returns one Pair. Families are registered in
# FAMILIES at the bottom. To add one: write it, register it, and make sure validate() passes
# for a few thousand seeds (tests do this).


def _comparison(rng: random.Random, i: int) -> Pair:
    """Relational comparison. The relation word is the load-bearing fact."""
    a, b = rng.sample(NAMES, 2)
    dim, hi, lo = rng.choice(
        [("height", "taller", "shorter"), ("age", "older", "younger"),
         ("speed", "faster", "slower"), ("wealth", "richer", "poorer")]
    )
    q = f" Question: who is {lo}? Answer:"
    return Pair(
        canonical=Item(
            prompt=f"{a} is {hi} than {b}.{q}",
            options=(f" {a}", f" {b}"), correct_index=1,
            family="comparison", variant="canonical", pair_id=f"comparison-{i}",
        ),
        perturbed=Item(
            prompt=f"{a} is {lo} than {b}.{q}",
            options=(f" {a}", f" {b}"), correct_index=0,
            family="comparison", variant="perturbed", pair_id=f"comparison-{i}",
        ),
    )


def _transitive(rng: random.Random, i: int) -> Pair:
    """Two-step transitive chain. Reversing the chain flips which end is extremal."""
    a, b, c = rng.sample(NAMES, 3)
    hi, lo = rng.choice([("older", "younger"), ("taller", "shorter"), ("faster", "slower")])
    q = f" Question: who is the {hi.replace('er', 'est')}? Answer:"
    return Pair(
        canonical=Item(
            prompt=f"{a} is {hi} than {b}. {b} is {hi} than {c}.{q}",
            options=(f" {a}", f" {c}"), correct_index=0,
            family="transitive", variant="canonical", pair_id=f"transitive-{i}",
        ),
        perturbed=Item(
            prompt=f"{a} is {lo} than {b}. {b} is {lo} than {c}.{q}",
            options=(f" {a}", f" {c}"), correct_index=1,
            family="transitive", variant="perturbed", pair_id=f"transitive-{i}",
        ),
    )


def _negation(rng: random.Random, i: int) -> Pair:
    """Presence/absence of a single negation particle."""
    obj = rng.choice(OBJECTS)
    name = rng.choice(NAMES)
    q = " Question: does the drawer contain something? Answer:"
    return Pair(
        canonical=Item(
            prompt=f"{name} checked the drawer. The drawer is not empty; the {obj} is inside.{q}",
            options=(" yes", " no"), correct_index=0,
            family="negation", variant="canonical", pair_id=f"negation-{i}",
        ),
        perturbed=Item(
            prompt=f"{name} checked the drawer. The drawer is empty; the {obj} is elsewhere.{q}",
            options=(" yes", " no"), correct_index=1,
            family="negation", variant="perturbed", pair_id=f"negation-{i}",
        ),
    )


def _arithmetic(rng: random.Random, i: int) -> Pair:
    """One digit changes. Options stay fixed, so recall of either number cannot help."""
    name = rng.choice(NAMES)
    obj = rng.choice(["apples", "coins", "cards", "stamps"])
    start = rng.randint(6, 19)
    give_a = rng.randint(1, start - 3)
    result_a = start - give_a
    # pick a second removal that yields a different, still-positive result
    give_b = rng.choice([g for g in range(1, start) if start - g != result_a and start - g > 0])
    result_b = start - give_b
    q = f" Question: how many {obj} does {name} have now? Answer:"
    return Pair(
        canonical=Item(
            prompt=f"{name} had {start} {obj} and gave away {give_a}.{q}",
            options=(f" {result_a}", f" {result_b}"), correct_index=0,
            family="arithmetic", variant="canonical", pair_id=f"arithmetic-{i}",
        ),
        perturbed=Item(
            prompt=f"{name} had {start} {obj} and gave away {give_b}.{q}",
            options=(f" {result_a}", f" {result_b}"), correct_index=1,
            family="arithmetic", variant="perturbed", pair_id=f"arithmetic-{i}",
        ),
    )


def _role_swap(rng: random.Random, i: int) -> Pair:
    """Dative role assignment, perturbed by reversing the *verb*, not the names.

    The obvious construction — swap the two names — is broken, and measurably so. Swapping
    names also swaps their positions, so "answer the last-named entity" gets **both** members
    right and scores a perfect flip rate. E001 seed 0 caught exactly that: gpt2 scored 0.98
    here while scoring at chance everywhere else, and the larger models scored *worse* as
    they moved away from pure recency.

    Reversing the verb instead holds both names in place, so position carries no information
    and a recency heuristic gives the same answer twice — flip rate 0, as it should be.
    """
    a, b = rng.sample(NAMES, 2)
    obj = rng.choice(OBJECTS)
    q = f" Question: who has the {obj} now? Answer:"
    return Pair(
        canonical=Item(
            prompt=f"{a} gave the {obj} to {b}.{q}",
            options=(f" {a}", f" {b}"), correct_index=1,
            family="role_swap", variant="canonical", pair_id=f"role_swap-{i}",
        ),
        perturbed=Item(
            prompt=f"{a} received the {obj} from {b}.{q}",
            options=(f" {a}", f" {b}"), correct_index=0,
            family="role_swap", variant="perturbed", pair_id=f"role_swap-{i}",
        ),
    )


def _conditional(rng: random.Random, i: int) -> Pair:
    """Modus ponens vs modus tollens.

    Both directions are *valid*. The invalid partners (affirming the consequent, denying the
    antecedent) leave the answer under-determined and are deliberately not used — an
    ambiguous item scores a reasoning model as wrong.
    """
    name = rng.choice(NAMES)
    ante, cons = rng.choice(
        [("it rains", "the match is cancelled"),
         ("the alarm rings", "the door locks"),
         ("the light is green", "the gate opens")]
    )
    # Phrased as "is it true that <clause>?" so the question stays grammatical and uniform
    # across antecedents, and the tense matches the premises. Constructing an interrogative
    # from a present-tense clause ("did the alarm rings?") produces ungrammatical prompts,
    # which is a confound: the model is then partly being scored on malformed English.
    q = f" Question: is it true that {ante}? Answer:"
    return Pair(
        canonical=Item(  # modus ponens: consequent held ⇒ compatible; state antecedent held
            prompt=f"{name} knows that if {ante}, then {cons}. In fact {ante}, "
                   f"and so {cons}.{q}",
            options=(" yes", " no"), correct_index=0,
            family="conditional", variant="canonical", pair_id=f"conditional-{i}",
        ),
        perturbed=Item(  # modus tollens: consequent failed ⇒ antecedent must have failed
            prompt=f"{name} knows that if {ante}, then {cons}. In fact it is not true that "
                   f"{cons}.{q}",
            options=(" yes", " no"), correct_index=1,
            family="conditional", variant="perturbed", pair_id=f"conditional-{i}",
        ),
    )


FAMILIES: dict[str, Callable[[random.Random, int], Pair]] = {
    "comparison": _comparison,
    "transitive": _transitive,
    "negation": _negation,
    "arithmetic": _arithmetic,
    "role_swap": _role_swap,
    "conditional": _conditional,
}


def _swap_options(item: Item) -> Item:
    """Reverse an item's option order, moving the correct index with it."""
    return Item(
        prompt=item.prompt,
        options=(item.options[1], item.options[0]),
        correct_index=1 - item.correct_index,
        family=item.family,
        variant=item.variant,
        pair_id=item.pair_id,
    )


def generate(
    n_per_family: int = 100,
    seed: int = 0,
    families: list[str] | None = None,
) -> list[Pair]:
    """Generate a fresh, seeded, never-published pair set.

    Two balance properties, both load-bearing:

    * **Exact, per pair** — each pair contributes one correct answer at index 0 and one at
      index 1, so a model answering a constant option scores exactly 0 flip rate no matter
      which option it favours.
    * **Approximate, per variant** — option order is swapped for a random half of the pairs,
      so canonical items within a family do not all share the same correct index. Without
      this, canonical accuracy would measure a model's option bias as much as its reasoning.
    """
    chosen = families or list(FAMILIES)
    unknown = set(chosen) - set(FAMILIES)
    if unknown:
        raise ValueError(f"unknown families: {sorted(unknown)}; have {sorted(FAMILIES)}")

    rng = random.Random(seed)
    pairs: list[Pair] = []
    for family in chosen:
        make = FAMILIES[family]
        for i in range(n_per_family):
            pair = make(rng, i)
            if rng.random() < 0.5:
                # Swap both members together — options must stay identical across the pair.
                pair = Pair(_swap_options(pair.canonical), _swap_options(pair.perturbed))
            pair.validate()
            pairs.append(pair)
    return pairs


def flatten(pairs: list[Pair]) -> list[Item]:
    """Pairs → a flat item list for batched scoring."""
    return [item for pair in pairs for item in (pair.canonical, pair.perturbed)]
