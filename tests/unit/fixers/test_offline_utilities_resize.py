"""resize_image_container: spinner wraps the qemu-img wait; shrink / no-op paths."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from h2kvm.fixers.offline.helpers.utilities import OfflineUtilities

_MOD = "h2kvm.fixers.offline.helpers.utilities"


def _util() -> OfflineUtilities:
    return OfflineUtilities(logger=MagicMock())


def test_no_resize_requested_returns_none():
    assert _util().resize_image_container(Path("/x.qcow2"), None) is None
    assert _util().resize_image_container(Path("/x.qcow2"), "") is None


def test_dry_run_skips_resize():
    out = _util().resize_image_container(Path("/x.qcow2"), "+1G", dry_run=True)
    assert out == {"image_resize": "skipped", "dry_run": True}


def test_resize_runs_qemu_img_inside_progress_context():
    util = _util()
    events: list[str] = []

    class _Progress:
        def __enter__(self):
            events.append("enter")

        def __exit__(self, *exc):
            events.append("exit")
            return False

    proc = MagicMock()
    proc.returncode = 0
    proc.wait.side_effect = lambda: events.append("wait")
    popen = MagicMock()
    popen.return_value.__enter__.return_value = proc

    with (
        patch(f"{_MOD}.Convert.qemu_img_info", return_value={"virtual-size": 1 << 30}),
        patch(f"{_MOD}.subprocess.Popen", popen),
        patch(f"{_MOD}.blinking_progress", return_value=_Progress()) as spinner,
    ):
        util.resize_image_container(Path("/x.qcow2"), "+1G")

    spinner.assert_called_once()
    assert spinner.call_args.args[1] == "Resizing image"
    assert events == ["enter", "wait", "exit"]
