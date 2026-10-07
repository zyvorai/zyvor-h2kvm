# Where h2kvm fits in the Zyvor suite

How GuestKit, h2kvm, Kairon, Veyron, Machina and the other Zyvor products relate.

[Back to the README](../README.md) · [Documentation index](README.md)

---

[GuestKit](https://zyvor.dev/guestkit) and [h2kvm](https://zyvor.dev/h2kvm) fix the disk and land the VM. Where it lands decides the Zyvor product you run it on: on Kubernetes that is [Kairon](https://github.com/zyvorai/kairon), with [Veyron](https://github.com/zyvorai/veyron) as the command center; for a private cloud on your own hosts it is [Machina](https://zyvor.dev/machina). KubeVirt and OpenStack are legacy targets. See [How it works](how-it-works.md).

| Product | Role |
|---------|------|
| [GuestKit](https://github.com/zyvorai/guestkit) | Offline disk repair before power-on |
| **h2kvm** *(this repo)* | Pick up, repair, convert, and land the VM on Kairon or Machina |
| [Transiva](https://github.com/zyvorai/transiva) | vSphere · Nutanix export (separate repo) |
| [Kairon](https://github.com/zyvorai/kairon) | Kubernetes endpoint (`--deploy-kairon`): real VMs straight on KVM, 0 pods per VM |
| [Veyron](https://github.com/zyvorai/veyron) | The API h2kvm calls for Kairon, plus the console, CLI, day-2 ops, SSO and SOC |
| [Machina](https://zyvor.dev/machina) | Private-cloud endpoint (`--emit-domain-xml`): Fleet Cloud, HA/DRS, eBPF datapath, Zyra AI, installed with one command |
| [PacketWolf](https://zyvor.dev/packetwolf) | Kernel-native network intelligence |

## Legacy endpoints

For VMs landed with `--deploy-k8s` on KubeVirt. h2kvm has no API link to these products.

| Product | Role |
|---------|------|
| [Zorvia](https://github.com/zyvorai/zorvia) | KubeVirt endpoint: craft and watch VMs |
| [Zeus OS](https://zyvor.dev/zeus-os) | KubeVirt endpoint: visual infrastructure OS |

→ [zyvor.dev](https://zyvor.dev) · [hypervisor exit program](https://zyvor.dev/hypervisor-exit)
