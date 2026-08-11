"""Scoring a causal LM on paired items by option log-likelihood.

Why log-likelihood rather than generation: the models in scope start at 124M parameters and
cannot reliably follow an instruction or an output format. Generating and parsing would
measure format compliance and call the result reasoning. Scoring both candidate
continuations directly removes that failure mode — there is nothing to parse, every model
produces a usable answer, and small base models are compared on the same footing as
instruction-tuned ones.

Both aggregations are recorded because they can disagree and the disagreement is
informative:

* ``sum`` — total log-probability of the option. Favours shorter options.
* ``mean`` — per-token average. Length-normalised, but flattens genuinely long answers.

Options within a pair are identical strings by construction, so this choice cannot change
which model looks better — but it is recorded rather than assumed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import torch

from .device import DeviceInfo, autocast_dtype, get_device_info
from .items import Item


@dataclass
class LoadedModel:
    model: object
    tokenizer: object
    name: str
    n_params: int
    device_info: DeviceInfo

    @property
    def n_params_millions(self) -> float:
        return round(self.n_params / 1e6, 1)


def load_model(name: str, device_info: DeviceInfo | None = None) -> LoadedModel:
    """Load a causal LM onto the resolved device in the best supported dtype."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    info = device_info or get_device_info()
    tokenizer = AutoTokenizer.from_pretrained(name)
    if tokenizer.pad_token is None:
        # Padded positions are masked out of every gather, so the choice is cosmetic —
        # but transformers refuses to batch without one.
        tokenizer.pad_token = tokenizer.eos_token

    dtype = autocast_dtype(info)
    model, loading_info = AutoModelForCausalLM.from_pretrained(
        name, dtype=dtype, output_loading_info=True
    )

    # A checkpoint whose keys do not match the installed architecture gets the missing
    # tensors **randomly initialised**, and transformers only warns. The model then loads,
    # runs, and produces a plausible-looking score for a partly-random network.
    #
    # Caught on HuggingFaceTB/nanowhale-100m-base (DeepseekV4ForCausalLM): shared_experts
    # and hc_head weights were newly initialised, and it scored 0.013 flip rate — a number
    # that would have read as "tiny model cannot reason" rather than "we evaluated noise".
    # Refuse to score such a model.
    missing = list(loading_info.get("missing_keys", []))
    if missing:
        preview = ", ".join(missing[:5])
        raise RuntimeError(
            f"{name}: {len(missing)} weight(s) missing from the checkpoint and randomly "
            f"initialised ({preview}{'…' if len(missing) > 5 else ''}). Scoring this would "
            "measure noise. Upgrade transformers to a version matching the model's "
            "architecture, or drop the model from the ladder and say so in the writeup."
        )
    # Cast device AND dtype together. `dtype=` at load time does not always convert every
    # module — a checkpoint with mixed-precision tensors leaves some in fp32, which then
    # fails at the first matmul with "expected mat1 and mat2 to have the same dtype".
    # Caught on HuggingFaceTB/nanowhale-100m-base.
    model.to(device=info.device, dtype=dtype)
    model.eval()

    return LoadedModel(
        model=model,
        tokenizer=tokenizer,
        name=name,
        n_params=sum(p.numel() for p in model.parameters()),
        device_info=info,
    )


@torch.no_grad()
def _score_batch(
    loaded: LoadedModel,
    prompts: list[str],
    continuations: list[str],
) -> list[tuple[float, int]]:
    """Log-probability of each continuation given its prompt.

    Returns ``(sum_logprob, n_tokens)`` per input.
    """
    tok = loaded.tokenizer
    device = loaded.device_info.device

    prompt_ids = [tok(p, add_special_tokens=False)["input_ids"] for p in prompts]
    cont_ids = [tok(c, add_special_tokens=False)["input_ids"] for c in continuations]

    # A continuation that tokenizes to nothing would silently score 0.0 and win every
    # comparison. Guard rather than debug it later.
    for cont, ids in zip(continuations, cont_ids, strict=True):
        if not ids:
            raise ValueError(f"continuation {cont!r} tokenized to zero tokens")

    sequences = [p + c for p, c in zip(prompt_ids, cont_ids, strict=True)]
    max_len = max(len(s) for s in sequences)
    pad_id = tok.pad_token_id

    input_ids = torch.full((len(sequences), max_len), pad_id, dtype=torch.long)
    attention = torch.zeros((len(sequences), max_len), dtype=torch.long)
    for row, seq in enumerate(sequences):
        input_ids[row, : len(seq)] = torch.tensor(seq, dtype=torch.long)
        attention[row, : len(seq)] = 1

    input_ids = input_ids.to(device)
    attention = attention.to(device)

    logits = loaded.model(input_ids=input_ids, attention_mask=attention).logits
    # float32 for the softmax: bf16 log_softmax loses enough precision to flip close calls.
    logprobs = torch.log_softmax(logits.float(), dim=-1)

    out: list[tuple[float, int]] = []
    for row, (p_ids, c_ids) in enumerate(zip(prompt_ids, cont_ids, strict=True)):
        start = len(p_ids)
        total = 0.0
        for offset, token_id in enumerate(c_ids):
            # logits at position i predict the token at i+1
            total += logprobs[row, start + offset - 1, token_id].item()
        out.append((total, len(c_ids)))
    return out


def evaluate_items(
    loaded: LoadedModel,
    items: Iterable[Item],
    batch_size: int = 16,
    aggregation: str = "sum",
    progress: object | None = None,
) -> list[dict]:
    """Score every item, returning one per-item record per item.

    Per-item records are mandatory, not optional detail: an aggregate without them cannot
    be re-analysed and is worth much less six months later.
    """
    if aggregation not in ("sum", "mean"):
        raise ValueError(f"aggregation must be 'sum' or 'mean', got {aggregation!r}")

    items = list(items)
    # One row per (item, option); both options of an item stay in the same batch.
    flat_prompts: list[str] = []
    flat_conts: list[str] = []
    for item in items:
        for option in item.options:
            flat_prompts.append(item.prompt)
            flat_conts.append(option)

    scores: list[tuple[float, int]] = []
    for start in range(0, len(flat_prompts), batch_size):
        scores.extend(
            _score_batch(
                loaded,
                flat_prompts[start : start + batch_size],
                flat_conts[start : start + batch_size],
            )
        )
        if progress is not None:
            progress(min(start + batch_size, len(flat_prompts)), len(flat_prompts))

    records: list[dict] = []
    for idx, item in enumerate(items):
        pair_scores = scores[2 * idx : 2 * idx + 2]
        sums = [s for s, _ in pair_scores]
        means = [s / n for s, n in pair_scores]
        ranked = sums if aggregation == "sum" else means
        chosen = int(max(range(2), key=lambda i: ranked[i]))
        records.append(
            {
                "pair_id": item.pair_id,
                "family": item.family,
                "variant": item.variant,
                "prompt": item.prompt,
                "options": list(item.options),
                "correct_index": item.correct_index,
                "chosen_index": chosen,
                "correct": chosen == item.correct_index,
                "logprob_sum": [round(s, 4) for s in sums],
                "logprob_mean": [round(m, 4) for m in means],
                "margin": round(abs(ranked[0] - ranked[1]), 4),
            }
        )
    return records
