# h2kvm — Documentation

Enterprise VM migration — any hypervisor to KVM

## Start Here

| Goal | Document |
|------|----------|
| Quick start | [README.md#60-second-quick-start](../README.md#60-second-quick-start) |
| **Deploy to Kairon (through Veyron)** | [deployment/kairon-deployment.md](deployment/kairon-deployment.md) |
| **Land on Machina** | [how-it-works.md#where-the-vm-lands](how-it-works.md#where-the-vm-lands) |
| **Remote lab deploy** | [deployment/deploy-remote.md](deployment/deploy-remote.md) |
| **GuestKit integration** | [architecture/GUESTKIT.md](architecture/GUESTKIT.md) |
| Kubernetes deploy (operator, Helm; legacy KubeVirt target) | [deployment/README.md](deployment/README.md) |
| Sources, disk pipeline and targets | [how-it-works.md](how-it-works.md) |
| Install, artifacts and surfaces | [install-and-quick-start.md](install-and-quick-start.md) |
| GuestKit in h2kvm | [guestkit-integration.md](guestkit-integration.md) |
| Remote lab deploy (commands) | [remote-lab-deploy.md](remote-lab-deploy.md) |
| Demos | [demos.md](demos.md) |
| Community vs Enterprise summary | [community-vs-enterprise.md](community-vs-enterprise.md) |
| The Zyvor suite | [zyvor-suite.md](zyvor-suite.md) |
| Examples | [../examples/](../examples/) |
| **User journeys & acceptance criteria** | [User Stories](USER_STORIES.md) |

## User Stories

Persona-based journeys with acceptance criteria: **[USER_STORIES.md](USER_STORIES.md)**

| Persona | Focus |
|---------|-------|
| Alex (Migration Engineer) | VMware/Hyper-V to KVM pipelines |
| Morgan (Windows Admin) | Win10/11 migration with driver fixes |
| Jordan (K8s Platform) | VMs on Kubernetes (Kairon; KubeVirt as legacy) |

## Ecosystem

Part of the [Zyvor / HyperSDK platform stack](https://zyvor.dev):

| Product | Role |
|---------|------|
| **kairon** | Real VMs on Kubernetes, 0 pods per VM; the `--deploy-kairon` target |
| **veyron** | Command center for Kairon; the API h2kvm calls for `--deploy-kairon` |
| **machina** | Private cloud for libvirt hosts; the `--emit-domain-xml` target |
| **hypercluster** | Kubernetes bootstrap |
| **zeus-os (v9s)** | Visual infrastructure OS for KubeVirt (legacy target) |
| **zorvia** | Craft and run KubeVirt VMs (legacy target) |
| **forge** | AI infrastructure on K8s |
| **h2kvm** | VM conversion + deploy (this repo's pipeline partner) |
| **guestkit** | Offline VM assurance (`hypersdk-guestkit`) |
| **packetwolf** | Network intelligence |
| **Aether** | Runtime portability |
| **hermes** | Application layer for K8s |

See also: [../README.md](../README.md)
