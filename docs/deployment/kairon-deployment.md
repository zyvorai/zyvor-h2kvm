# Deploy to Kairon (through Veyron)

`--deploy-kairon` boots the converted disk as a [Kairon](https://github.com/zyvorai/kairon)
`Machine`. It needs no KubeVirt, no CDI and no PVC upload: h2kvm fixes and converts the
disk as usual, then asks Veyron (`POST /api/v1/imports`) to create a Machine whose
`spec.image.source.httpURL` points at the disk, pinned by its sha256. kairon-node downloads
the file into its digest-keyed cache and boots a per-Machine overlay, so the disk survives
power-off and two VMs from the same image never share writes.

## What you need

- A Veyron API URL and a key with the **write** role (`--kairon-api-key` or `VEYRON_API_KEY`).
- A way for the Kairon node to fetch the disk over HTTP(S). Choose one:
  - **`--kairon-image-url`**: you already published the file (S3, an HTTP server, Atlas RGW).
  - **`--kairon-serve HOST:PORT` + `--kairon-advertise-url`**: h2kvm serves the file itself,
    at an unguessable path, until the VM reaches `Running`. The advertise URL is the base
    address nodes use to reach this machine.

## Examples

VMware VM, served from the conversion host:

```bash
h2kvmctl --config vmware-web01.yaml \
  --deploy-kairon \
  --kairon-veyron-url https://veyron.example:30151 --kairon-insecure \
  --kairon-namespace prod --kairon-cpus 4 --kairon-memory 8Gi \
  --kairon-serve 0.0.0.0:8099 --kairon-advertise-url http://10.0.0.5:8099 \
  --kairon-source-hypervisor vmware
```

Disk already on an internal web server, created stopped:

```bash
h2kvmctl --config hyperv-db01.yaml \
  --deploy-kairon --kairon-veyron-url https://veyron.example:30151 \
  --kairon-image-url https://files.example/db01.qcow2 --kairon-no-start
```

## Flags

| Flag | Meaning |
|---|---|
| `--kairon-namespace`, `--kairon-vm-name` | Where the Machine lands (name defaults to `--vm-name` or the file stem) |
| `--kairon-cpus`, `--kairon-memory` | Size (Veyron defaults: 2 vCPU, 4Gi) |
| `--kairon-repair` | Also run FluxVM's offline virtio repair. Usually unnecessary, since h2kvm already fixed the guest |
| `--kairon-secure-boot`, `--kairon-tpm` | Firmware security for Windows 11 / Server 2022 guests |
| `--kairon-no-start` | Create stopped (needs `--kairon-image-url`, because Kairon fetches the image at first boot) |
| `--kairon-wait-timeout` | Seconds to wait for `Running` (default 1800) |
| `--kairon-continue-on-error` | Keep the migration result if the deploy fails (default on) |

`--deploy-kairon` is mutually exclusive with `--deploy-k8s`, `--deploy-openstack` and the
local libvirt options. Imported VMs carry the label `veyron.io/imported-by=h2kvm` and the
source hypervisor/VM as annotations; list them with `GET /api/v1/imports?namespace=all`.
