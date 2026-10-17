// Copyright 2026 Zyvor · https://zyvor.dev
// SPDX-License-Identifier: Apache-2.0

import type {ReactNode} from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import {
  Actions,
  Band,
  Bento,
  Btn,
  CopyCommand,
  CtaBand,
  Frame,
  Grad,
  Headline,
  List,
  StatBar,
  Steps,
  SubNav,
  Terminal,
  TextLink,
} from '@site/src/components/zv';
import ScreenshotStrip from '@site/src/components/ScreenshotStrip';

const SUB_LINKS = [
  {to: '#how', label: 'How it works'},
  {to: '#lands', label: 'Where it lands'},
  {to: '#nutanix', label: 'Exit Nutanix'},
  {to: '#numbers', label: 'Numbers'},
  {to: '#product', label: 'Product'},
  {to: '#licensing', label: 'Licensing'},
];

function Hero() {
  return (
    <Band tone="black" glow center>
      <p>
        <TextLink to="/nutanix-exit">New: leaving Nutanix, end to end, with diagrams and a measured run</TextLink>
      </p>
      <Headline
        size="display"
        eyebrow="h2kvm · hypervisor exit"
        title={
          <>
            Any hypervisor
            <br />
            to <Grad>KVM.</Grad>
          </>
        }
        lede="Convert the disk offline. Fix the guest before power-on. Then land it on Kairon (real VMs on Kubernetes, 0 pods per VM) or Machina (the private cloud you install before lunch)."
      />
      <Actions>
        <Btn to="/docs/getting-started/quickstart">Get started</Btn>
        <Btn to="#how" variant="ghost">
          See how it works
        </Btn>
      </Actions>
      <Terminal
        title="h2kvmctl · local conversion"
        lines={[
          {kind: 'cmd', text: 'h2kvmctl --cmd local --vmdk disk.qcow2 --output-dir out \\'},
          {kind: 'out', text: '  --out-format qcow2 --flatten --fstab-mode stabilize-all \\'},
          {kind: 'out', text: '  --regen-initramfs --emit-domain-xml --checksum'},
          {kind: 'dim', text: '[*] inspecting the guest offline (GuestKit)'},
          {kind: 'dim', text: '[*] repairing fstab, initramfs and network before power-on'},
          {kind: 'info', text: '[*] converting to qcow2 and writing the checksum'},
          {kind: 'ok', text: '[+] disk, report and libvirt domain XML written'},
        ]}
      />
      <p className="zv-stat__note" style={{marginTop: '0.9rem'}}>
        Abridged and illustrative; the real run prints live logs and a JSON report.
      </p>
    </Band>
  );
}

function Problem() {
  return (
    <Band tone="soft" center>
      <Headline
        eyebrow="The problem"
        title={
          <>
            The disk leaves. <Grad>The guest has to boot.</Grad>
          </>
        }
        lede="Copying the disk was never the hard part. First boot fails when the bootloader, VirtIO or Windows still points at the old hypervisor. GuestKit repairs that on the disk, before power-on."
      />
      <div className="zv-two" style={{textAlign: 'left'}}>
        <div>
          <h3>How the disk gets out</h3>
          <p className="zv-note">
            On 10 September 2026 VMware told The Register the Virtual Disk Development Kit was never a license to move
            VMs. Most VMware-to-KVM tools still open disks with that kit. h2kvm does not: the disk leaves through the
            vSphere API and NFS.
          </p>
        </div>
        <div>
          <h3>What it handles</h3>
          <List
            items={[
              'vSphere over HTTPS, ESXi over SSH, Azure, or a disk file you already have.',
              'Bootloader, VirtIO and Windows repaired while the disk is offline.',
              'A VMDK, VHDX or raw file becomes qcow2, then the same repair step runs.',
            ]}
          />
        </div>
      </div>
    </Band>
  );
}

function How() {
  return (
    <Band tone="light" id="how" center>
      <Headline
        eyebrow="How it works"
        title={
          <>
            Four stages. <Grad>Nothing powered on until it is fixed.</Grad>
          </>
        }
      />
      <Steps
        steps={[
          {title: '1 · Export', body: 'Pick the disk up where it lives: vSphere, ESXi, Azure, Nutanix through Transiva, or a file.'},
          {title: '2 · Repair', body: 'GuestKit inspects the guest offline and fixes boot, drivers, fstab and network.'},
          {title: '3 · Convert', body: 'Flatten and convert to qcow2, with a checksum and a JSON report.'},
          {title: '4 · Land', body: 'Emit a libvirt domain, or hand off to Kairon through Veyron, or to a Machina host.'},
        ]}
      />
      <TextLink to="/docs/how-it-works">Read the full walkthrough ›</TextLink>
    </Band>
  );
}

function Lands() {
  return (
    <Band tone="soft" id="lands" center>
      <Headline
        eyebrow="Where it lands"
        title={
          <>
            Leave VMware. <Grad>Skip the next lock-in.</Grad>
          </>
        }
        lede="Plain qcow2 and a libvirt domain run anywhere KVM does. Kairon and Machina are the two first-class landing zones."
      />
      <Bento
        tiles={[
          {
            title: 'Kairon via Veyron',
            body: 'Real VMs scheduled by Kubernetes and run straight on KVM: 0 pods per VM, a 14x lighter idle control plane and 7.4x faster to SSH for five VMs than KubeVirt v1.9.0.',
            to: '/docs/how-it-works#why-kairon-and-machina-instead-of-kubevirt-and-openstack',
            variant: 'dark',
            more: 'Why Kairon ›',
          },
          {
            title: 'Machina',
            body: 'A private cloud of four Rust services and one install command on a single KVM host, not nine services on MariaDB and RabbitMQ.',
            to: '/docs/how-it-works#why-kairon-and-machina-instead-of-kubevirt-and-openstack',
            variant: 'blue',
            more: 'Why Machina ›',
          },
          {
            title: 'Plain KVM and libvirt',
            body: 'Boot the converted disk with the domain XML h2kvm emits.',
            to: '/nutanix-exit',
            more: 'See a run ›',
          },
          {
            title: 'KubeVirt and OpenStack',
            body: 'Kept as legacy targets for estates that already run them.',
            to: '/docs/how-it-works#where-the-vm-lands',
            more: 'Where the VM lands ›',
          },
        ]}
      />
    </Band>
  );
}

function Nutanix() {
  const map = useBaseUrl('/img/exit-system-map.svg');
  return (
    <Band tone="light" id="nutanix" center>
      <Headline
        eyebrow="New · Exit Nutanix"
        title={
          <>
            Out of Nutanix <Grad>in minutes.</Grad>
          </>
        }
        lede="Transiva exports the VM through Prism v4. h2kvm repairs and converts it. It boots on plain KVM."
      />
      <Frame
        src={map}
        alt="Nutanix is exported by Transiva into a qcow2 and manifest; h2kvm repairs and converts it; it lands on KVM, KubeVirt, Kairon or Machina."
        caption="The system map. Solid targets were run; dashed ones were not."
      />
      <Actions>
        <Btn to="/nutanix-exit">What h2kvm does after the export</Btn>
        <Btn to="https://zyvorai.github.io/zyvor-transiva/docs/marketing/exit-nutanix.html" variant="ghost">
          The whole picture
        </Btn>
      </Actions>
    </Band>
  );
}

function Numbers() {
  return (
    <Band tone="black" id="numbers" center>
      <Headline
        eyebrow="Numbers"
        title={
          <>
            Measured, <Grad>not promised.</Grad>
          </>
        }
      />
      <StatBar
        stats={[
          {value: 0, label: 'pods per VM', note: 'on Kairon'},
          {value: 14, suffix: 'x', label: 'lighter idle', note: 'control plane vs KubeVirt v1.9.0'},
          {value: 7.4, decimals: 1, suffix: 'x', label: 'faster to SSH', note: 'five VMs, vs KubeVirt v1.9.0'},
        ]}
      />
    </Band>
  );
}

function Product() {
  return (
    <Band tone="soft" id="product" center>
      <Headline
        eyebrow="Product"
        title={
          <>
            A real product, <Grad>not a mockup.</Grad>
          </>
        }
        lede="h2kvmctl for the pipeline. h2kweb for jobs, providers and status, captured against a live lab deployment."
      />
      <ScreenshotStrip bare />
    </Band>
  );
}

function Licensing() {
  return (
    <Band tone="light" id="licensing" center>
      <Headline
        eyebrow="Licensing"
        title={
          <>
            Free for non-production. <Grad>Paid for production.</Grad>
          </>
        }
        lede="Development, testing, evaluation and labs are free under the Zyvor Production License. Production use is $100 per VM, one-time, or Enterprise at a fixed price from $2,500/month."
      />
      <Actions>
        <Btn to="/docs/licensing">Read the licensing guide</Btn>
        <Btn to="/resources" variant="ghost">
          Resources
        </Btn>
      </Actions>
      <CopyCommand label="Copy install command">{'pip install "h2kvm[guestkit]"'}</CopyCommand>
    </Band>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="h2kvm — any hypervisor to KVM"
      description="Convert VMs from vSphere, Azure, Nutanix and any disk image to KVM. The guest is fixed before power-on, then lands on Kairon via Veyron or a Machina private cloud.">
      <SubNav title="h2kvm" links={SUB_LINKS} cta={{to: '/docs/getting-started/quickstart', label: 'Get started'}} />
      <main>
        <Hero />
        <Problem />
        <How />
        <Lands />
        <Nutanix />
        <Numbers />
        <Product />
        <Licensing />
        <CtaBand title="Convert your first VM." lede="Install from PyPI for a lab. Book a demo when the wave needs a named owner.">
          <Btn to="/docs/getting-started/quickstart">Quickstart</Btn>
          <Btn to="https://zyvor.dev/contact?intent=demo&utm_source=github&utm_medium=h2kvm&utm_campaign=docs_site" variant="ghost">
            Book a demo
          </Btn>
        </CtaBand>
      </main>
    </Layout>
  );
}
