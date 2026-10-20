# AI review (h2kvm)

_Generated 2026-10-20 by claude-opus-5-5 from a snapshot of tracked sources; verify before acting._

# Code Review: h2kvm

## Summary
h2kvm is a Python toolchain (`h2kvmctl`/`h2kvm`) that converts VMware, Hyper-V, Azure and other VM disks to qcow2 for KVM. It repairs guests offline through the external GuestKit package (`hypersdk-guestkit`), then deploys to libvirt/Machina, Kairon, or legacy KubeVirt/OpenStack. Around that core the repo ships a daemon, a worker REST API, Kubernetes operators and Helm/OLM bundles, a LUKS/TPM auto-unlock subsystem, a web dashboard, packaging, and a very large docs and marketing tree.

Most of what I could see is README/Markdown. Many findings below are therefore inconsistencies between documents, or between documents and claimed behavior, rather than verified code defects.

## Bugs and correctness risks

**`upload-to-kubevirt.sh`**
- The upload proxy URL is built from `$(kubectl get service -n cdi cdi-uploadproxy -o jsonpath='{.spec.clusterIP}')`, unquoted and inline.
  - If the service lookup fails, `set -e` does not catch it, because the substitution is inside an argument. The script then calls `https://:443`.
  - A ClusterIP is also usually unreachable from outside the cluster.
- There is no check that `$QCOW2_IMAGE` exists before uploading.
- The script ends by telling the user to apply `kubevirt-rhel8.8-deployment.yaml`. That file is not shown, so it may not exist.
- The defaults (`rhel-vms`, `rhel8.8-fixed.qcow2`) are leftovers from a specific lab setup.

**`k8s/README.md`**
- The HPA example targets `kind: DaemonSet`. HPA cannot scale DaemonSets, so this example cannot work.
- `base/psp.yaml` (PodSecurityPolicy) is listed. PSP was removed in Kubernetes 1.25, yet `docs/deployment/README.md` claims support for 1.24–1.33.

**Two overlapping operators**
- `operator/` contains:
  - a Go/kubebuilder-style operator (`make build`, `HyperConversion` CRD);
  - an OLM bundle at v1.2.0.
- `olm/` contains a v2.0.0 bundle with `MigrationJob`/`JobTemplate` CRDs.
- `h2kvm/runtime/operator/` describes a Python/kopf operator.
- It is unclear which one ships. CRD names (`hyperconversions.h2kvm.io` vs `migrationjobs.h2kvm.io`) and image names conflict.

**`images/worker-api/README.md`**
- The Kubernetes example runs `replicas: 3` against a single PVC.
- `docs/worker/README.md` says the queue is SQLite/Redis. With SQLite on a shared, likely ReadWriteOnce, volume, multiple replicas will either fail to schedule or corrupt state.

**Module path mismatches (verify against code)**

| Where | Path used | Conflicts with |
|---|---|---|
| Helm, k8s docs | `python3 -m h2kvm.worker.cli` | `h2kvm/runtime/README.md` documents `h2kvm.runtime.worker.*` |
| `h2kvm/orchestration/profiles/README.md` | `from h2kvm.profiles import ProfileLoader` | the README lives under `orchestration/` |

**Hook stage names differ across docs**
- `examples/hooks/` uses `pre_fix` and `post_convert`.
- `h2kvm/infrastructure/README.md` uses `post-fixing` and `post-migration`, plus an `ansible` hook type.
- One of these is wrong.

**Broken library examples**
- `docs/api/README.md` imports `guestkit_client` and then uses an undefined `GuestKit` class.
- `docs/reference/api/README.md` imports from a nonexistent-looking `h2kvm.guestkit.main`. It also calls `open_guest("disk.qcow2")` and then `add_drive_opts` on a different disk.

**Conflicting CLI surface**
- `docs/ux/readme-how-it-works.html` says "One pipeline, no subcommands".
- `docs/guides/cli/README.md` documents `h2kvmctl convert/fetch/inspect`.
- `docs/worker/README.md` documents `h2kvmctl submit/status/cancel`.
- Config keys also differ: `command:` in the docs vs `cmd:` in `test-confs/`.
- In `docs/getting-started/README.md`, the "Or using h2kvm" example repeats `h2kvmctl`.

## Security concerns

**LUKS secrets (`h2kvm/luks/README.md`, `contrib/README.md`)**
- The Vault token is stored in plaintext in `/etc/h2kvm/luks.json`.
- The token is also passed as `--vault-token s.xxx` on the command line, which exposes it in `ps` output and shell history. This contradicts the "No secrets in cmdline" claim.
- Troubleshooting steps use `curl -k`.
- The "Security Audit ✅" list is asserted, not evidenced.

**Hooks (`examples/hooks/README.md`)**
- Template values such as `{{ vm_name }}` are substituted into script args and env. These values come from manifests, so this is an injection risk unless args are passed as an argv list and values are validated.
- Python hooks import arbitrary modules.
- `h2kvm/infrastructure/README.md` claims checksum/signature validation and sandboxing. The hooks example only mentions `U.safe_path()`, so the claim needs verification.

**Worker API**
- It binds `0.0.0.0` by default.
- The example exposes it through `type: LoadBalancer`.
- No authentication is documented for job submission. Jobs drive privileged disk operations, so this is serious.

**Privilege and isolation**
- Workers and fixer Jobs run `privileged: true` with hostPath.
- The namespace is labelled `enforce=privileged`.
- `docs/testing/README.md` recommends `chmod 666 /dev/kvm`.

**Remote deploy (`scripts/deploy-remote.sh`)**
- It accepts a password as a positional argument or through `DEPLOY_PASS`.
- It sets `/var/lib/h2kvm` to mode 755.
- It runs `pip install --break-system-packages`.

**Release pipeline (`.github/workflows/README.md`)**
- It instructs creating a PyPI token with "Entire account" scope.
- A project-scoped token or PyPI Trusted Publishing should be used instead.

**Mutable image tags**
- Defaults use `:latest` (operator, `quay.io/h2kvm/fixer:latest`).
- Registries are inconsistent: `ghcr.io/ssahani` vs `ghcr.io/zyvorai`. This complicates supply-chain verification.

## Test and CI gaps

**Test and coverage claims contradict each other**

| Source | Claim |
|---|---|
| `docs/test-results/` | 450+ tests, 87.5% coverage |
| `docs/reference/api/README.md` | "100%" |
| `h2kvm/pipeline/README.md` | "28 tests, 100% passing" |

None of these is backed by CI artifacts visible here.

**`.codecov.yml`**
- It ignores `setup.py`, but the project appears to use hatch/pyproject.
- Patch coverage is `informational: true`, so it never blocks merges.

**Docs CI example (`docs/testing/README.md`)**
- It uses `actions/checkout@v2`.
- It runs on a kind runner, which has no KVM/NBD. The test suite there cannot meaningfully exercise conversion.

**Integration and E2E coverage**
- Real-VM/E2E tests (`tests/integration/real_vms`, phony guests requiring root) appear to be manual only.
- No CI job is evident for the operator(s), Helm lint/template, OLM `bundle validate`, or ShellCheck. The latter matters for scripts like `upload-to-kubevirt.sh`.

**Unverifiable workflow references**
- `.github/workflows/README.md` references `docs.yml` and `pylint.yml`.
- `website/README.md` references `pages.yml`.
- I cannot verify these exist.

## Documentation gaps

**Licensing is contradictory.**
- `docs/legal/README.md` says the Zyvor Production License.
- Several READMEs say Apache-2.0: `examples/libvirt-xml`, `completions`, `h2kvm/luks`, `h2kvm/pipeline`, `operator`.
- `systemd` and `contrib` say Proprietary.

**Repo URLs are inconsistent.** I found `ssahani/h2kvm`, `zyvorai/h2kvm`, `zyvorai/zyvor-h2kvm`, and `anthropics/h2kvm`. The last is almost certainly wrong; it appears in `docs/roadmap`, `contrib`, and `h2kvm/luks`. Also, `website/README.md` enables Pages on `zyvorai/h2kvm` but serves from `zyvor-h2kvm`.

**Version numbers conflict.** Values include 0.2.1 (debian), 0.2.2 (k8s), 0.3.0, 0.3.1, v1.2.0, v2.0.0, v2.1.0, and "v2.2.0+".

**Dates conflict.** "Architecture (August 2026)" and a benchmark dated 2026-10-04 sit alongside "Last Updated March 2026".

**Likely broken relative links.**
- `h2kvm/orchestration/profiles/README.md` uses `../docs/...`.
- `examples/workflow-daemon/README.md` links `docs/Daemon-Mode.md`, while other docs use `docs/10-Daemon-Mode.md`.
- Many numbered `docs/0X-*.md` paths conflict with the `getting-started/` layout.

**Placeholders and non-technical material.**
- `docs/runbooks/README.md` lists `support@example.com` as the vendor support contact.
- Marketing/LinkedIn playbooks and legal templates are mixed into the technical docs.

**Unsupported performance and success-rate claims.** These include "7x faster LVM", "100% host protection", and per-OS success rates, all without reproducible methodology.

## Top 5 recommended actions (ordered)

1. **Lock down the worker API and hooks.**
   - Add authentication and authorization to job submission.
   - Stop recommending a public LoadBalancer.
   - Pass hook args as an argv list, never through a shell, and validate templated values.
2. **Remove secrets from the CLI and plaintext config.**
   - Remove `--vault-token`/password arguments; use files with 0600 permissions, or Kubernetes Vault auth.
   - Switch PyPI publishing to Trusted Publishing.
   - Pin image tags or digests.
3. **Pick one operator and one CRD set.**
   - Decide between `operator/` (HyperConversion) and `olm/` + `runtime/operator` (MigrationJob).
   - Delete or clearly deprecate the other.
   - Drop the PSP manifest and fix the DaemonSet HPA example.
4. **Fix licensing and identity metadata.**
   - Make every README match `LICENSE`.
   - Use one canonical repo URL and registry.
   - Remove the `anthropics/` links.
   - Use a single version source.
5. **Add CI that verifies the docs' claims.**
   - Run ShellCheck on scripts and harden `upload-to-kubevirt.sh` (quote the substitution, fail on an empty proxy URL, check the image exists).
   - Add Helm lint/template and `operator-sdk bundle validate` jobs.
   - Add a link checker and doctests for the library API examples.
   - Publish real coverage numbers in place of the hand-written statistics.
