---
sidebar_position: 2
---

# How it works

![h2kvm talks to vSphere over HTTPS. vCenter SOAP, ESXi NFC lease, then the disk.](/h2kvm-vsphere-path.jpg)

The disk is fixed before it is powered on. h2kvm picks a disk up from wherever the VM lives today, repairs the guest offline, converts it to qcow2, and lands it on Kairon (through Veyron) or a Machina libvirt host. KubeVirt and OpenStack remain as legacy targets.

![h2kvm picks up disks from vSphere, ESXi, Azure and local files, repairs them offline with GuestKit, converts to qcow2, then deploys to Kairon through the Veyron API or a Machina libvirt host, with KubeVirt and OpenStack as legacy targets.](/h2kvm-flow.svg)

## Where disks come from

There are no subcommands and no `--source` flag. Pick the mode with `--cmd`, or `cmd:` in a YAML config passed with `--config`.

| Source | How h2kvm picks it up | Entry point | Status |
|---|---|---|---|
| vSphere (govc) | `govc export.ovf` pulls the OVF and disks over an HTTPS NFC lease. h2kvm packs the OVA itself | `--cmd vsphere --vcenter … --vs-vm …` | Implemented |
| vSphere (datastore) | `GET /folder/…` over HTTPS with the vCenter session, resumable | `--cmd vsphere --vs-download-only` | Implemented |
| vSphere (ovftool) | VMware's `ovftool`, if you have it installed | `--cmd vsphere --ovftool-path …` | Implemented, external binary |
| ESXi over SSH | Streams the disk with `ssh … cat`, with progress | `--cmd fetch-and-fix --host … --remote …` | Implemented |
| Azure | `az` CLI: snapshot, SAS URL, ranged HTTPS download | `--cmd azure --azure-resource-group …` | Implemented |
| Files you already have | Disk on the machine running h2kvm. The qemu-img format comes from the suffix | `--cmd local --vmdk FILE` (any format), or `ova`, `ovf`, `vhd`, `raw`, `ami` | Implemented |
| Folder or manifest | The daemon watches a folder. `--manifest` runs a declarative 8-stage pipeline | `--cmd daemon`, `--manifest FILE` | Implemented |
| Nutanix AHV | Not in this repo. Transiva does the NFS pickup, then you feed the file to `--cmd local` | — | Via Transiva |
| AWS, Proxmox Backup Server | Library modules only, not reachable from the CLI | — | Not exposed |
| GCP, Xen, VirtualBox, remote Hyper-V | No pickup code. Their disk files (VDI, VHDX) work as local files | — | Not implemented |

## What happens to the disk

1. **Pick up.** Extract an OVA or VHD, or download the disk, then discover the disk files.
2. **Inspect and flatten.** VMDKs are inspected first. `--flatten` merges a snapshot chain into one working image.
3. **Repair offline.** GuestKit runs `run_migrate_repair` on the disk image, then h2kvm injects cloud-init, first-boot, network, user, service and hostname config.
4. **Convert and check.** `qemu-img convert` to qcow2, then `qemu-img check` on the result.
5. **Deploy, or stop.** Hand the qcow2 to one target below, or keep the file.

## Where the VM lands

![Where it lands: Kairon + Veyron on Kubernetes, Machina as the private cloud, KubeVirt and OpenStack as legacy targets](/readme-where-it-lands.jpg)

| Target | What h2kvm does | Enable with | Zyvor product on top |
|---|---|---|---|
| Kairon on Kubernetes | Asks Veyron (`POST /api/v1/imports`) to create a Kairon `Machine` whose image points at the converted disk over HTTP(S), pinned by sha256. kairon-node boots it straight on KVM: no pod, no KubeVirt, no CDI, no PVC upload | `--deploy-kairon` | Kairon runs the VM; Veyron is the console, API and day-2 ops |
| Machina libvirt host | Emits the domain XML and, with `--virsh-define`, runs `virsh define` on the host h2kvm runs on | `--emit-domain-xml` | Machina is the private cloud for those hosts: Fleet Cloud, HA/DRS, eBPF, Zyra AI |

- **One target per run.** The CLI and web API reject combining them.
- **Kairon is a native integration.** h2kvm calls the Veyron API with a key that has the write role (`--kairon-api-key` or `VEYRON_API_KEY`).
- **Machina manages the host afterwards.** h2kvm defines the VM on a libvirt host; it has no API link to Machina itself.

### Why Kairon and Machina instead of KubeVirt and OpenStack

![Kairon vs KubeVirt and Machina vs OpenStack, side by side](/readme-vs-kubevirt-openstack.jpg)

| | Ours | Legacy |
|---|---|---|
| VMs on Kubernetes | **Kairon**: 0 pods per VM, 63 MiB idle control plane, 24.8 s to SSH for 5 VMs (p50) | **KubeVirt**: a `virt-launcher` pod per VM, 905 MiB, 184.7 s |
| Private cloud | **Machina**: 4 Rust services, embedded SQLite, `./machinactl deploy` on one host | **OpenStack**: 9+ services, MariaDB/Galera and RabbitMQ, a Kolla-Ansible project |

Kairon numbers: same node and guest, run back to back against KubeVirt v1.9.0 on 2026-10-04 ([Kairon benchmark](https://github.com/zyvorai/kairon/blob/main/docs/benchmarks/kairon-vs-kubevirt.md)).

### Legacy targets

Still supported for teams that cannot move yet. New deployments should land on Kairon or Machina.

| Target | What h2kvm does | Enable with | Notes |
|---|---|---|---|
| KubeVirt cluster | Uploads the disk (containerDisk, CDI `virtctl image-upload`, or a PVC copy), then creates a `kubevirt.io/v1` VirtualMachine on whatever cluster your kubeconfig points at | `--deploy-k8s` | Zorvia and Zeus OS can operate those VMs; no API link from h2kvm |
| OpenStack | openstacksdk uploads the qcow2 to Glance and can boot a Nova server. Endpoints come from the Keystone catalog | `--deploy-openstack` | Third-party cloud. A failed Glance or Nova step is logged and the run still succeeds by default |

## The Zyvor products

| Product | What it does | Site | Repo |
|---|---|---|---|
| GuestKit | Inspects the disk offline so you know it is safe before power-on | [zyvor.dev/guestkit](https://zyvor.dev/guestkit) | [zyvorai/guestkit](https://github.com/zyvorai/guestkit) |
| h2kvm | Any hypervisor to KVM. The guest is fixed so the VM boots the first time | [zyvor.dev/h2kvm](https://zyvor.dev/h2kvm) | [zyvorai/h2kvm](https://github.com/zyvorai/h2kvm) |
| Kairon | Real VMs on Kubernetes, straight on KVM, 0 pods per VM | — | [zyvorai/kairon](https://github.com/zyvorai/kairon) |
| Veyron | The command center for virtual machines on Kubernetes | [zyvorai.github.io/veyron](https://zyvorai.github.io/veyron/) | [zyvorai/veyron](https://github.com/zyvorai/veyron) |
| Machina | Your metal, your cloud, one control plane | [zyvor.dev/machina](https://zyvor.dev/machina) | [zyvorai/machina](https://github.com/zyvorai/machina) |
| Zorvia | Craft and run KubeVirt VMs (legacy KubeVirt target) | [zyvor.dev/zorvia](https://zyvor.dev/zorvia) | [zyvorai/zorvia](https://github.com/zyvorai/zorvia) |
| Zeus OS | The visual infrastructure OS for KubeVirt (legacy KubeVirt target) | [zyvor.dev/zeus-os](https://zyvor.dev/zeus-os) | [zyvorai/zeus-os](https://github.com/zyvorai/zeus-os) |

First boot fails when the bootloader, VirtIO, or Windows still points at the old hypervisor. GuestKit does that work before power-on. Kairon and Veyron keep the VM running on Kubernetes; Machina keeps it running on your own hosts.
