# Toolchain

## Platforms

**Windows and Linux are both first-class. macOS is not a target.**

Practically this means: assume CUDA, assume an NVIDIA GPU, and do not write code that
depends on Metal/MPS or on POSIX-only behaviour. Two rules cover most of it:

- Build paths with `pathlib.Path`, never string concatenation with `/`.
- Anything that shells out gets a Windows path *and* a Linux path, or gets replaced with a
  Python equivalent.

Where a platform difference is unavoidable, isolate it in one function and note it. CI, if
we add it, runs both.

## Python

Managed entirely by [uv](https://docs.astral.sh/uv/). uv installs the interpreter too, so
there is no system Python to corrupt.

```powershell
# Windows
irm https://astral.sh/uv/install.ps1 | iex
```
```bash
# Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

uv lands in `~/.local/bin`. Add it to PATH if your shell does not pick it up.

Per project:

```bash
cd projects/001-geometric-reasoning
uv sync                  # resolves + installs into ./.venv from pyproject.toml + uv.lock
uv run <command>         # runs inside that venv, no activation needed
```

**Never** `pip install` globally, and never activate one project's venv while working in
another. Each project pins its own dependency set on purpose — projects are allowed to
disagree about library versions, and that is cheaper than a shared environment that
nobody can upgrade.

`uv.lock` **is** committed. Reproducibility is the whole point.

## PyTorch and CUDA

You do not need the CUDA Toolkit installed. PyTorch wheels ship their own CUDA runtime;
only the NVIDIA **driver** has to be present on the machine.

Projects select the CUDA wheel index explicitly in `pyproject.toml` rather than relying on
whatever PyPI serves by default — the default is often the CPU build, which fails silently
by being slow instead of erroring.

The CUDA Toolkit (`nvcc`) is only required when compiling custom CUDA kernels. Install it
then, not before.

Verify a project's environment:

```bash
uv run python -m geomreason.doctor
```

That prints torch version, CUDA availability, device name, VRAM, and a matmul smoke test.
If `cuda_available` is `False`, the wheel is wrong — fix it before running anything else,
because everything will "work" and just be 50× slower.

## C / C++ / native code

Some work here will want a native extension: a custom kernel, a fast tokenizer, a tight
inner loop that Python cannot carry. Policy:

- Reach for it only when a measurement says Python is the bottleneck. Write the Python
  version first; it is the correctness reference for the fast version.
- Prefer, in order: `numpy`/`torch` vectorisation → `numba` → Cython/`pybind11` → raw CUDA.
- Native code lives in `src/<pkg>/_native/` with a pure-Python fallback and a test that
  asserts the two agree.

Compilers:

- **Linux**: `gcc`/`g++` from the distro, plus `python3-dev`.
- **Windows**: MSVC Build Tools (the "Desktop development with C++" workload). This is a
  multi-GB install; do it when a project actually needs it, not upfront.
  Download: <https://aka.ms/vs/17/release/vs_BuildTools.exe>

  ```powershell
  # silent install of just the C++ workload
  .\vs_BuildTools.exe --quiet --wait --norestart `
    --add Microsoft.VisualStudio.Workload.VCTools `
    --includeRecommended
  ```

Keep native code optional. A project that cannot run at all without a compiler is a
project nobody will rerun in a year.

## Hardware baseline

The reference machine for this repo:

| | |
|---|---|
| GPU | NVIDIA RTX 3090, 24 GB VRAM, Ampere (sm_86) |
| CPU | AMD Ryzen 7 5700X3D — 8 cores / 16 threads |
| RAM | 64 GB |
| Disk | ~1.8 TB free |
| Driver | 582.53 |

What that buys you:

- Full fine-tuning of models up to roughly **1–1.5B** parameters with AdamW, and up to
  ~7B with LoRA/QLoRA. Anything larger is inference-only.
- Comfortable full pretraining of **GPT-2 scale (124M)** models from scratch — hours, not
  weeks. Most of this repo's experiments are sized to land here deliberately, because it
  is the scale at which you can afford to run the same thing five times with different
  seeds and actually learn something.
- Ampere supports `bf16` and TF32. Turn both on; there is no accuracy reason not to.

Rules of thumb worth knowing before designing a run:

- Full fine-tune VRAM ≈ 16 bytes/parameter with AdamW (weights + grads + two optimizer
  moments, mixed precision). 24 GB / 16 B ≈ 1.5B parameters before activations.
- Activation memory scales with `batch × sequence_length`. Gradient checkpointing trades
  ~30% speed for a large activation saving — usually the right trade here.
- Set `torch.backends.cuda.matmul.allow_tf32 = True` and use `bf16` autocast on Ampere.

## Determinism

Seeds go in the config, not in the code. Every run records the seed alongside its results.

Full bitwise determinism on GPU costs real speed (`torch.use_deterministic_algorithms(True)`
plus `CUBLAS_WORKSPACE_CONFIG`), so it is off by default. Instead we run **multiple seeds
and report the spread** — which is more honest anyway, since a result that only holds for
one seed was never a result.
