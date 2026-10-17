import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import SystemMap from '@site/static/img/exit-system-map.svg';
import Sequence from '@site/static/img/exit-sequence.svg';
import styles from './nutanix-exit.module.css';

const TRANSIVA = 'https://zyvorai.github.io/zyvor-transiva/docs/marketing';

const STAGES = [
  {
    n: '1',
    t: 'Export',
    p: 'Transiva pulls the disk out of Nutanix over Prism v4 and writes a qcow2 plus artifact-manifest.json. h2kvm starts from that disk.',
    b: 'Transiva · run',
    ok: true,
  },
  {
    n: '2',
    t: 'Repair',
    p: 'GuestKit inspects the guest offline and fixes what stops it booting on KVM (fstab, initramfs, drivers). Nothing is powered on first.',
    b: 'skipped on the test image',
    ok: false,
  },
  {
    n: '3',
    t: 'Convert',
    p: 'Flatten, convert to qcow2 and checksum. In the unattended run this took 32 s.',
    b: 'run · 32 s',
    ok: true,
  },
  {
    n: '4',
    t: 'Land',
    p: 'Emit a libvirt domain, or hand off to Kairon through Veyron. libvirt/KVM and KubeVirt booted; Kairon and Machina were not run.',
    b: 'KVM, KubeVirt run',
    ok: true,
  },
];

export default function NutanixExit(): ReactNode {
  return (
    <Layout
      title="Exit Nutanix"
      description="What h2kvm does after Transiva exports a VM out of Nutanix: repair, convert and land on KVM, KubeVirt, Kairon or Machina.">
      <div className={styles.page}>
        <header className={styles.hero}>
          <div className={styles.eyebrow}>EXIT NUTANIX · THE H2KVM SIDE</div>
          <h1 className={styles.title}>
            Exported. Now make it <em>boot</em>.
          </h1>
          <p className={styles.lead}>
            Transiva gets the disk out of Nutanix. h2kvm repairs it offline,
            converts it and lands it, so the VM runs on plain KVM or KubeVirt.
          </p>
          <Link className={styles.cta} href={`${TRANSIVA}/exit-nutanix.html`}>
            The whole picture
          </Link>
          <Link className={styles.cta} href="/docs/getting-started/quickstart">
            h2kvm quickstart
          </Link>
        </header>

        <section className={styles.section}>
          <h2>Where h2kvm sits</h2>
          <p className={styles.sub}>
            A VM leaves Nutanix as a qcow2 plus a manifest. h2kvm is the middle:
            it makes that disk bootable and puts it where it will run.
          </p>
          <div className={styles.dia}>
            <SystemMap role="img" />
          </div>
        </section>

        <section className={styles.section}>
          <h2>Four stages</h2>
          <p className={styles.sub}>What each stage did in the recorded run.</p>
          <div className={styles.stages}>
            {STAGES.map((s) => (
              <div key={s.n} className={styles.stage}>
                <span className={styles.num}>STAGE {s.n}</span>
                <b>{s.t}</b>
                <p>{s.p}</p>
                <span className={`${styles.badge} ${s.ok ? styles.ok : ''}`}>
                  {s.b}
                </span>
              </div>
            ))}
          </div>
          <div className={styles.code}>
            {`# the exact conversion from the unattended run
h2kvmctl --cmd local --vmdk <exported.qcow2> --output-dir <dir> \\
  --out-format qcow2 --flatten --fstab-mode stabilize-all \\
  --regen-initramfs --emit-domain-xml --checksum \\
  --report <dir>/report.json`}
          </div>
        </section>

        <section className={styles.section}>
          <h2>Order of calls</h2>
          <div className={styles.dia}>
            <Sequence role="img" />
          </div>
        </section>

        <section className={styles.section}>
          <h2>Straight talk</h2>
          <div className={styles.cols}>
            <div className={styles.col}>
              <h3>What ran</h3>
              <ul>
                <li>Export, convert and boot, 7 of 7 stages, 145 s</li>
                <li>Boot on libvirt/KVM (35 s) and KubeVirt (75 s)</li>
                <li>The guest answered ping, 0% loss</li>
              </ul>
            </div>
            <div className={styles.col}>
              <h3>Known h2kvm gaps</h3>
              <ul>
                <li>
                  Guest inspection found no root filesystem on the Alpine test
                  image, so repair was skipped (the run still passed).
                </li>
                <li>
                  The emitted domain XML had <code>graphics type='both'</code>,
                  which libvirt rejected; it was changed to <code>vnc</code> by
                  hand.
                </li>
                <li>Windows, UEFI, multi-disk and large VMs were not run.</li>
                <li>Kairon and Machina landings were not run.</li>
              </ul>
            </div>
          </div>
          <p className={styles.note}>
            The Prism endpoint in the run was Chimera, a simulator, not a real
            Nutanix cluster.
          </p>
        </section>
      </div>
    </Layout>
  );
}
