Drop this file at the root of your project repo so Claude Code (or any AI coding assistant) understands the cluster environment you're working on. Edit the `noahsabb` line before checking in.

---

## Environment

- **Cluster**: shared 32× H100 SLURM cluster, 4 nodes × 8 GPUs (H100 80GB HBM3).
- **My username on the cluster**: `noahsabb` ← edit this
- **My home directory**: `/home/noahsabb` (on a shared Weka filesystem mounted on the login pod and all workers).
- **Access**: via Omniva-issued kubeconfig. Connection model is `kubectl exec` into my LoginSet pod; there is no SSH and no port-forward to external services.
- **My login pod selector**: `kubectl get pod -n slurm -l stanford/user=noahsabb`
- **Pod name pattern**: `slurm-login-noahsabb-<hash>`

## How to do anything compute-heavy

NEVER run training, evaluation, container pulls, or other GPU-bound work inside the login pod. The login pod is a small CPU shell with no GPU. All compute goes through `sbatch` to a SLURM partition. Single-node only.

### Submitting a job

```bash
sbatch myjob.sbatch
squeue -u $USER        # see my queue
sacct -u $USER -S today
scancel <jobid>
```

### sbatch template

```bash
#!/bin/bash
#SBATCH --partition=small        # see "Partitions" below
#SBATCH --gres=gpu:1             # request N GPUs (1–8)
#SBATCH --time=00:30:00          # max walltime; required
#SBATCH --output=%x-%j.out
#SBATCH --job-name=my-run

# ... my commands here ...
```

### With a container (pyxis + enroot)

```bash
srun --gres=gpu:1 --cpus-per-task=16 \
  --container-image='nvcr.io#nvidia/pytorch:24.12-py3' \
  python train.py
```

**Two rules that will bite you if you skip them:**

- **Always pass `--cpus-per-task=16` on container jobs.** The first time an image is used on a worker, enroot builds a squashfs of it (~20 GB for PyTorch). That build is single-threaded by default and uses only the CPUs SLURM gave the job — with the default 2 CPUs, it takes ~30 minutes. With 16 CPUs, ~3 minutes. After the first build the squashfs is cached on that worker for free.
- **Image reference syntax rule.** For Docker Hub images use the **bare name** (`alpine:latest`, `python:3.12-slim`). For any other registry use the `<registry>#<path>` URI form (`nvcr.io#nvidia/pytorch:24.12-py3`). The specific combination `docker.io#library/<name>` breaks enroot's manifest pipeline (JSON parse error). NGC images are still preferred for ML work — they ship CUDA + NCCL + cuDNN matched to host drivers and avoid Docker Hub rate limits.

Common working images:
- `nvcr.io#nvidia/pytorch:24.12-py3` — PyTorch 2.x + CUDA + NCCL + most ML libs
- `nvcr.io#nvidia/cuda:12.6.0-base-ubuntu22.04` — minimal CUDA base
- `nvcr.io#nvidia/cuda:12.6.0-devel-ubuntu22.04` — has nvcc + headers for compiling

### Sanity-check the cluster

If something feels broken, run this from the login pod to verify pyxis + container imports work end-to-end:

```bash
srun --partition=small --gres=gpu:1 --cpus-per-task=16 \
  --container-image='nvcr.io#nvidia/pytorch:24.12-py3' \
  python -c "import torch; print(torch.cuda.device_count())"
```

Should print `1`. If it hangs at `pyxis: importing` for more than ~5 min on the first run, ping the admin — the worker's enroot scratch directory may have lost its permissions.

## Partitions

| Partition | Max walltime | Use for |
|---|---|---|
| `small`  | 24h | single-GPU jobs, quick experiments |
| `medium` | 5d  | multi-GPU runs, longer training |
| `big`    | 5d  | large reserved slots — restricted access |

Default partition is `small`. If a longer run is needed, use `medium`.

## GPU-hour budget

I have a per-user GPU-hour cap enforced by SLURM QoS. When the cap is hit, new jobs queue indefinitely until reset.

```bash
sshare -u $USER                                    # remaining budget
sacctmgr show qos qos-$USER format=GrpTRESMins     # absolute cap (in minutes)
```

When suggesting workloads:
- Prefer fewer, larger jobs over many small ones (fewer prolog/epilog cycles).
- Check feasibility against the remaining budget before suggesting a sweep.
- Default to `--gres=gpu:1` unless multi-GPU is required; multi-GPU multiplies hour consumption.

## Storage

- `/home/noahsabb` — my primary workspace. Persistent across pods + nodes.
- `/home/_shared/models` — read-only shared HuggingFace cache. Use it if a model is already there before downloading.
- `/home/_shared/datasets` — read-only shared dataset cache.
- Soft cap is ~1 TB per user. Avoid hoarding checkpoints; delete or move old runs.

## Login-pod context

- Container runs as `root` by default. To act as me (so file ownership in `/home/noahsabb` is correct), run interactive shells via `runuser`:
  ```bash
  kubectl exec -it -n slurm <my-pod> -c login -- runuser -u noahsabb -- bash -l
  ```
- I have these pre-installed on the login pod: `python3`, `pip`, `uv`, `git`, `git-lfs`, `gh`, `rsync`, `aws` (CLI v2), `huggingface_hub[cli]`, `wandb`, `transformers`, `tokenizers`, `datasets`, `vim`, `tmux`, `htop`, `jq`.
- For heavy Python deps (torch, vllm, deepspeed, etc.), put them in the container image used by `srun --container-image=`, not on the login pod.

## Copying files

```bash
# from my laptop into my pod's home dir
kubectl cp local-file.py slurm/<my-pod>:/home/noahsabb/local-file.py -c login

# from pod back to laptop
kubectl cp slurm/<my-pod>:/home/noahsabb/results.tar.gz . -c login
```

## Constraints to remember when suggesting code

- **No SSH-into-the-cluster** patterns. No `ssh slurm-controller`, no rsync-over-ssh. All file movement uses `kubectl cp` or pulls/pushes via the network (HTTPS, S3, HF Hub).
- **No port-forwarding to external services.** I can't expose a Jupyter or TensorBoard port to the public internet. For interactive notebooks, run Jupyter inside an `srun --pty` session and port-forward via `kubectl port-forward <my-pod>` to my laptop only.
- **Single-node only.** The Stanford partitions (`small`, `medium`, `big`) all have `MaxNodes=1`. Don't suggest multi-node DDP. Use 1–8 GPUs on one node with `torchrun --standalone --nproc-per-node=N`.
- **No `sudo` on the login pod** (well, I'm root, but anything I install isn't persistent across pod restarts — bake into container images or use `pip install --user`).
- **All my actions on the cluster are audit-logged in Teleport.** Don't suggest probing other namespaces or other students' pods.

## Things that will likely come up

- **NCCL / multi-GPU**: the workers have RoCE v2 over 8× ConnectX-7 NDR (400 GbE). NCCL env is pre-injected by Kyverno policy on GPU jobs. Don't override `NCCL_IB_*` or `NCCL_SOCKET_IFNAME` unless I know what I'm doing.
- **Container caching**: enroot caches imported containers under `/run/enroot/${UID}` (per-job ephemeral). The first pull of a large image takes minutes; subsequent jobs reuse the cache for the duration of the worker pod's life.
- **Out-of-memory / OOM**: SLURM allocates the full node's memory by default when you take a GPU. If a job crashes with OOM, it's usually CUDA OOM (model too big for GPU memory), not host OOM.

## Container-specific gotchas (NGC 24.12-py3)
- Use `python3`, not `python` — `python` is not on PATH in this container
- Use `python3 -m torch.distributed.run`, not `torchrun` — torchrun is not on PATH
- Do NOT pip install/upgrade: torch, transformers, bitsandbytes, peft, accelerate, 
  datasets — container ships versions matched to nightly torch; overwriting breaks ABI
- Install trl with: `pip install -q --no-deps --break-system-packages "trl==0.13.0"`
- Other small deps: `pip install -q --break-system-packages tyro rich awscli`
