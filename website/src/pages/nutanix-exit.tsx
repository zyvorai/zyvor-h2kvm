// Copyright 2026 Zyvor · https://zyvor.dev
// SPDX-License-Identifier: Apache-2.0

import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import SystemMap from '@site/static/img/exit-system-map.svg';
import Sequence from '@site/static/img/exit-sequence.svg';
import {
  Actions,
  Band,
  Bento,
  Btn,
  CtaBand,
  Frame,
  Grad,
  Headline,
  List,
  Pill,
  StatBar,
  Steps,
  Terminal,
} from '@site/src/components/zv';
import run from '@site/src/data/exit-run.json';
import styles from './nutanix-exit.module.css';

const TRANSIVA = 'https://zyvorai.github.io/zyvor-transiva/docs/marketing';
const MAX = Math.max(...run.stages.map((s) => s.seconds));

function Timings() {
  return (
    <div className={styles.bars}>
      {run.stages.map((s) => (
        <div key={s.label} className={styles.row}>
          <span>{s.label}</span>
          <span className={styles.track}>
            <span
              className={`${styles.fill} ${s.accent ? styles.accent : ''}`}
              style={{width: `${Math.max(3, (s.seconds / MAX) * 100)}%`, display: 'block'}}
            />
          </span>
          <span className={styles.value}>{s.text}</span>
        </div>
      ))}
    </div>
  );
}

export default function NutanixExit(): ReactNode {
  return (
    <Layout
      title="Exit Nutanix"
      description="What h2kvm does after Transiva exports a VM out of Nutanix: repair, convert and land on KVM, KubeVirt, Kairon or Machina.">
      <div className={styles.vars}>
        <Band tone="black" glow center>
          <Headline
            size="display"
            eyebrow="Exit Nutanix · the h2kvm side"
            title={
              <>
                Exported. Now make it <Grad>boot.</Grad>
              </>
            }
            lede="Transiva gets the disk out of Nutanix. h2kvm repairs it offline, converts it and lands it, so the VM runs on plain KVM or KubeVirt."
          />
          <Actions>
            <Btn to={`${TRANSIVA}/exit-nutanix.html`}>The whole picture</Btn>
            <Btn to="/docs/getting-started/quickstart" variant="ghost">
              h2kvm quickstart
            </Btn>
          </Actions>
          <Terminal
            title="e2e-nutanix-exit.sh"
            lines={[
              {kind: 'cmd', text: './scripts/e2e-nutanix-exit.sh user@kvm-host'},
              {kind: 'dim', text: '== export with hyperexport (Prism v4 + NFS pickup)'},
              {kind: 'ok', text: 'PASS export'},
              {kind: 'dim', text: '== convert with h2kvm'},
              {kind: 'ok', text: 'PASS convert'},
              {kind: 'dim', text: '== boot on libvirt/KVM'},
              {kind: 'ok', text: 'PASS boot on KVM'},
            ]}
          />
          <p className="zv-stat__note" style={{marginTop: '0.9rem'}}>
            Abridged. The recorded numbers are further down this page.
          </p>
        </Band>

        <Band tone="soft" center>
          <Headline
            eyebrow="Where h2kvm sits"
            title={
              <>
                The middle of <Grad>the exit.</Grad>
              </>
            }
            lede="A VM leaves Nutanix as a qcow2 plus a manifest. h2kvm makes that disk bootable and puts it where it will run."
          />
          <Frame alt="Nutanix is exported by Transiva into a qcow2 and manifest, repaired and converted by h2kvm, and landed on KVM, KubeVirt, Kairon or Machina.">
            <div className={styles.diagram}>
              <SystemMap role="img" />
            </div>
          </Frame>
        </Band>

        <Band tone="light" center>
          <Headline
            eyebrow="Four stages"
            title={
              <>
                What each stage <Grad>did.</Grad>
              </>
            }
          />
          <Steps
            steps={[
              {title: '1 · Export', body: 'Transiva pulls the disk out of Nutanix over Prism v4 and writes a qcow2 plus artifact-manifest.json.'},
              {title: '2 · Repair', body: 'GuestKit inspects the guest offline and fixes what stops it booting on KVM. If a guest has no network configuration at all, h2kvm installs a DHCP fallback.'},
              {title: '3 · Convert', body: 'Flatten, convert to qcow2 and checksum, with a JSON report.'},
              {title: '4 · Land', body: 'Emit a libvirt domain, or hand off to Kairon through Veyron. KVM and KubeVirt were booted; Kairon and Machina were not run.'},
            ]}
          />
        </Band>

        <Band tone="soft" center>
          <Headline
            eyebrow="Order of calls"
            title={
              <>
                Who calls <Grad>whom.</Grad>
              </>
            }
          />
          <Frame alt="Order of calls: the script runs hyperexport, which negotiates Prism v4, reads the disk from NFS and converts it; then runs h2kvm and boots the result.">
            <div className={styles.diagram}>
              <Sequence role="img" />
            </div>
          </Frame>
        </Band>

        <Band tone="black" center>
          <Headline
            eyebrow="The run"
            title={
              <>
                Measured, <Grad>not promised.</Grad>
              </>
            }
            lede={`Image: ${run.image}. ${run.note}`}
          />
          <StatBar
            stats={[
              {value: run.passed, suffix: ` / ${run.total}`, label: 'stages passed', note: 'unattended'},
              {value: run.seconds, suffix: ' s', label: 'end to end', note: 'download to running guests'},
              {value: run.landed, suffix: ' / 2', label: 'targets booted', note: 'KVM (UEFI) and KubeVirt'},
            ]}
          />
          <Timings />
        </Band>

        <Band tone="light" center>
          <Headline
            eyebrow="Straight talk"
            title={
              <>
                What it does and <Grad>doesn&apos;t prove.</Grad>
              </>
            }
          />
          <div className="zv-two" style={{textAlign: 'left'}}>
            <div>
              <h3>
                What ran <Pill ok>verified</Pill>
              </h3>
              <List
                items={[
                  'Export, convert and boot, unattended, in one script',
                  'Ubuntu 24.04 boots on libvirt/KVM (UEFI) and on KubeVirt, guest answers ping',
                  'A guest with no network config comes up through the DHCP fallback',
                  'Prism endpoint was Chimera, a simulator, not a real cluster',
                ]}
              />
            </div>
            <div>
              <h3>What did not run</h3>
              <List
                limits
                items={[
                  'A real Nutanix cluster',
                  'Windows, multi-disk and large VMs',
                  'Boot repair on a guest that needs it (the Ubuntu image needed only the network fallback)',
                  'Kairon and Machina landings',
                  'Checks inside the guest beyond ping',
                ]}
              />
            </div>
          </div>
        </Band>

        <CtaBand title="Try it on your own host." lede="One script, no clicks.">
          <Btn to={`${TRANSIVA}/exit-nutanix.html`}>The whole picture</Btn>
          <Btn to="/docs/getting-started/quickstart" variant="ghost">
            h2kvm quickstart
          </Btn>
        </CtaBand>
      </div>
    </Layout>
  );
}
