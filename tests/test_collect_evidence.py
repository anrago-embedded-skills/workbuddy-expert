"""Host-side behavioral tests for the POSIX-shell evidence collector."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = (
    ROOT
    / "embedded-software-architect"
    / "skills"
    / "embedded-debug-workflow"
    / "scripts"
    / "collect-evidence.sh"
)
MAX_SOURCE_BYTES = 65_536
MAX_LINES = 120
MAX_LINE_CHARS = 240


class CollectEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.base = Path(self.tempdir.name)
        self.source = self.base / "snapshot"
        self.source.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.command_log = self.base / "host-command-calls.txt"
        self.install_host_command_sentinels()

    def install_host_command_sentinels(self) -> None:
        for name in ("uname", "dmesg"):
            wrapper = self.bin / name
            wrapper.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' '{name}' >> \"$HOST_COMMAND_LOG\"\n"
                f"printf '%s\\n' 'HOST_{name.upper()}_SENTINEL'\n",
                encoding="utf-8",
            )
            wrapper.chmod(0o755)

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env["HOST_COMMAND_LOG"] = str(self.command_log)
        return env

    def invoke(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/sh", str(COLLECTOR), *args],
            text=True,
            capture_output=True,
            env=env or self.environment(),
            check=False,
        )

    def install_live_shims(self, dmesg_body: str) -> dict[str, str]:
        (self.bin / "uname").write_text(
            "#!/bin/sh\nprintf '%s\\n' Linux\n", encoding="utf-8"
        )
        (self.bin / "dmesg").write_text(
            "#!/bin/sh\n" + dmesg_body + "\n", encoding="utf-8"
        )
        (self.bin / "uname").chmod(0o755)
        (self.bin / "dmesg").chmod(0o755)
        return self.environment()

    def restricted_environment(self, excluded: tuple[str, ...]) -> dict[str, str]:
        for name in ("awk", "wc", "cat", "mkdir", "rm", "head", "tail", "tr", "date"):
            if name in excluded or (self.bin / name).exists():
                continue
            executable = shutil.which(name)
            if executable:
                (self.bin / name).symlink_to(executable)
        return {"PATH": str(self.bin), "HOST_COMMAND_LOG": str(self.command_log)}

    def install_failing_cat(self, fail_at: int) -> dict[str, str]:
        cat_path = self.bin / "cat"
        if cat_path.exists() or cat_path.is_symlink():
            cat_path.unlink()
        cat_path.write_text(
            "#!/bin/sh\n"
            "count_file=\"$HOST_COMMAND_LOG.cat-count\"\n"
            "if [ -r \"$count_file\" ]; then read call_count < \"$count_file\"; else call_count=0; fi\n"
            "call_count=$((call_count + 1))\n"
            "printf '%s\\n' \"$call_count\" > \"$count_file\"\n"
            f"[ \"$call_count\" -eq {fail_at} ] && exit 42\n"
            "exec /bin/cat \"$@\"\n",
            encoding="utf-8",
        )
        cat_path.chmod(0o755)
        return self.restricted_environment(())

    def write_source(self, relative: str, data: str | bytes) -> Path:
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_bytes(data)
        return path

    def make_octal_looking_backslash_output(self) -> tuple[Path, Path, Path]:
        output = self.base / r"out\057escape"
        decoded_directory = self.base / "out" / "escape"
        decoded_directory.mkdir(parents=True)
        sentinel = decoded_directory / "keep.txt"
        sentinel.write_text("preserve outside directory\n", encoding="utf-8")
        return output, decoded_directory, sentinel

    def assert_no_output_escaped_to(self, decoded_directory: Path, sentinel: Path) -> None:
        self.assertEqual(
            {path.name for path in decoded_directory.iterdir()},
            {sentinel.name},
            "collector created a flag or other output outside the selected directory",
        )

    def collect(self, mode: str, name: str, *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        output = self.base / name
        result = self.invoke(
            "--mode",
            mode,
            "--output",
            str(output),
            "--source-root",
            str(self.source),
            *extra,
        )
        return result, output

    def manifest(self, output: Path) -> dict[str, object]:
        return json.loads((output / "manifest.json").read_text(encoding="utf-8"))

    def run_os_release_selector(self, source: Path) -> tuple[str, str]:
        script = COLLECTOR.read_text(encoding="utf-8")
        start_marker = "# BEGIN os-release source selection helpers\n"
        end_marker = "# END os-release source selection helpers\n"
        helpers = script.split(start_marker, 1)[1].split(end_marker, 1)[0]
        harness = (
            helpers
            + "\n"
            + "source_kind=live\n"
            + "source_root=$TEST_SOURCE_ROOT\n"
            + "append_item() { selected_name=$1; selected_source=$2; selected_output=$3; selected_status=$4; }\n"
            + "collect_file() { selected_name=$1; selected_source=$2; selected_output=$3; "
            + "if [ -f \"$source_root/$selected_source\" ]; then selected_status=collected; "
            + "else selected_status=missing; fi; }\n"
            + "collect_os_release\n"
            + "printf '%s\\n%s\\n' \"$selected_source\" \"$selected_status\"\n"
        )
        env = os.environ.copy()
        env["TEST_SOURCE_ROOT"] = str(source)
        result = subprocess.run(
            ["/bin/sh", "-c", harness],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        selected_source, selected_status = result.stdout.splitlines()
        return selected_source, selected_status

    def test_offline_environment_uses_only_snapshot_data_and_marks_provenance(self) -> None:
        self.write_source("proc/version", "Linux snapshot-kernel 6.1.0 #1\n")
        self.write_source("etc/os-release", "ID=fixture\nVERSION_ID=7\n")
        self.write_source("proc/cmdline", "console=ttyS0 root=/dev/mmcblk0\n")
        self.write_source("proc/meminfo", "MemTotal: 1024 kB\nMemAvailable: 256 kB\n")
        self.write_source("proc/swaps", "Filename Type Size Used Priority\n")
        self.write_source("proc/device-tree/model", b"Fixture Board\x00")
        self.write_source("proc/device-tree/compatible", b"vendor,fixture\x00vendor,soc\x00")

        result, output = self.collect("env", "env-output")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.manifest(output)
        self.assertEqual(manifest["source_kind"], "offline")
        self.assertEqual(manifest["source_root"], str(self.source.resolve()))
        self.assertEqual(manifest["mode"], "env")
        self.assertIn("snapshot-kernel", (output / "proc-version.txt").read_text())
        self.assertIn("Fixture Board", (output / "device-tree-model.txt").read_text())
        self.assertIn("vendor,soc", (output / "device-tree-compatible.txt").read_text())
        self.assertFalse(self.command_log.exists(), "offline mode called uname or dmesg")
        self.assertNotIn("HOST_UNAME_SENTINEL", "".join(p.read_text(errors="ignore") for p in output.iterdir() if p.is_file() and p.name != "manifest.json"))

    def test_offline_os_release_symlink_is_rejected_without_following_it(self) -> None:
        self.write_source("usr/lib/os-release", "ID=fixture-secret\n")
        link = self.source / "etc" / "os-release"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to("../usr/lib/os-release")

        result, output = self.collect("env", "offline-os-release-link")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        item = next(item for item in self.manifest(output)["items"] if item["name"] == "os-release")
        self.assertEqual(item["status"], "unsafe_path")
        self.assertFalse((output / "os-release.txt").exists())
        self.assertNotIn("fixture-secret", "".join(p.read_text(errors="ignore") for p in output.iterdir() if p.is_file()))

    def test_live_os_release_selector_allows_only_standard_lib_symlink_targets(self) -> None:
        relative = self.base / "relative-root"
        (relative / "etc").mkdir(parents=True)
        (relative / "usr" / "lib").mkdir(parents=True)
        (relative / "etc" / "os-release").symlink_to("../usr/lib/os-release")
        (relative / "usr" / "lib" / "os-release").write_text("ID=relative\n", encoding="utf-8")

        absolute = self.base / "absolute-root"
        (absolute / "etc").mkdir(parents=True)
        (absolute / "usr" / "lib").mkdir(parents=True)
        (absolute / "etc" / "os-release").symlink_to("/usr/lib/os-release")
        (absolute / "usr" / "lib" / "os-release").write_text("ID=absolute\n", encoding="utf-8")

        custom = self.base / "custom-root"
        (custom / "etc").mkdir(parents=True)
        (custom / "opt").mkdir(parents=True)
        (custom / "etc" / "os-release").symlink_to("../opt/os-release")
        (custom / "opt" / "os-release").write_text("ID=custom\n", encoding="utf-8")

        missing = self.base / "missing-canonical-root"
        (missing / "etc").mkdir(parents=True)
        (missing / "etc" / "os-release").symlink_to("../usr/lib/os-release")

        self.assertEqual(self.run_os_release_selector(relative), ("usr/lib/os-release", "collected"))
        self.assertEqual(self.run_os_release_selector(absolute), ("usr/lib/os-release", "collected"))
        self.assertEqual(self.run_os_release_selector(custom), ("etc/os-release", "unsafe_path"))
        self.assertEqual(self.run_os_release_selector(missing), ("usr/lib/os-release", "missing"))

    def test_offline_kernel_mode_reads_snapshot_log_without_calling_host_dmesg(self) -> None:
        self.write_source("var/log/kern.log", "[ 1.0] fixture kernel event\n")

        result, output = self.collect("kernel", "kernel-output")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("fixture kernel event", (output / "kernel-var-log-kern.log.txt").read_text())
        self.assertEqual(self.manifest(output)["source_kind"], "offline")
        self.assertFalse(self.command_log.exists(), "offline mode called dmesg")

    def test_offline_kernel_mode_retains_recent_log_tail_under_caps(self) -> None:
        old_records = "".join(f"record-{i:03d} " + "x" * 600 + "\n" for i in range(150))
        self.write_source("var/log/kern.log", old_records + "LATEST-OOM-EVENT\n")

        result, output = self.collect("kernel", "kernel-tail-output")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        captured = (output / "kernel-var-log-kern.log.txt").read_text(encoding="utf-8")
        self.assertIn("LATEST-OOM-EVENT", captured)
        self.assertNotIn("record-000", captured)
        item = next(item for item in self.manifest(output)["items"] if item["name"] == "kernel-kern-log")
        self.assertEqual(item["status"], "truncated")

    def test_offline_env_preserves_literal_backslash_output_path_and_truncation_flags(self) -> None:
        output, decoded_directory, sentinel = self.make_octal_looking_backslash_output()
        self.write_source("proc/version", "v" * 501 + "\n")
        self.write_source("proc/device-tree/model", b"m" * 501 + b"\x00")

        result = self.invoke(
            "--mode", "env", "--output", str(output), "--source-root", str(self.source)
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        items = {item["name"]: item for item in self.manifest(output)["items"]}
        with self.subTest(item="proc-version truncation status"):
            self.assertEqual(items["proc-version"]["status"], "truncated")
        with self.subTest(item="device-tree-model truncation status"):
            self.assertEqual(items["device-tree-model"]["status"], "truncated")
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {"proc-version.txt", "device-tree-model.txt", "manifest.json", "summary.txt"},
        )
        self.assertTrue((output / "proc-version.txt").is_file())
        self.assertTrue((output / "device-tree-model.txt").is_file())
        with self.subTest(item="output path confinement"):
            self.assert_no_output_escaped_to(decoded_directory, sentinel)

    def test_offline_kernel_tail_preserves_literal_backslash_output_path_and_truncation_flag(self) -> None:
        output, decoded_directory, sentinel = self.make_octal_looking_backslash_output()
        self.write_source("var/log/kern.log", "k" * 501 + "\n")

        result = self.invoke(
            "--mode", "kernel", "--output", str(output), "--source-root", str(self.source)
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        item = next(
            item for item in self.manifest(output)["items"] if item["name"] == "kernel-kern-log"
        )
        with self.subTest(item="kernel log truncation status"):
            self.assertEqual(item["status"], "truncated")
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {"kernel-var-log-kern.log.txt", "manifest.json", "summary.txt"},
        )
        with self.subTest(item="output path confinement"):
            self.assert_no_output_escaped_to(decoded_directory, sentinel)

    def test_live_kernel_mode_keeps_the_newest_bounded_dmesg_lines(self) -> None:
        dmesg_body = (
            "i=0\n"
            "while [ \"$i\" -lt 130 ]; do\n"
            "  printf 'record-%03d\\n' \"$i\"\n"
            "  i=$((i + 1))\n"
            "done\n"
            + "printf '%s\\n' '" + "w" * (MAX_LINE_CHARS + 60) + "'\n"
        )
        env = self.install_live_shims(dmesg_body)
        output = self.base / "live-kernel"
        result = self.invoke("--mode", "kernel", "--output", str(output), env=env)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = (output / "kernel-dmesg.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), MAX_LINES)
        self.assertEqual(lines[0], "record-011")
        self.assertEqual(lines[-1], "w" * MAX_LINE_CHARS)
        item = self.manifest(output)["items"][0]
        self.assertEqual(item["status"], "truncated")

    def test_mocked_live_dmesg_preserves_literal_backslash_output_path_and_truncation_flag(self) -> None:
        output, decoded_directory, sentinel = self.make_octal_looking_backslash_output()
        env = self.install_live_shims(
            "printf '%s\\n' '" + "d" * 501 + "'"
        )

        result = self.invoke("--mode", "kernel", "--output", str(output), env=env)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with self.subTest(item="dmesg truncation status"):
            self.assertEqual(self.manifest(output)["items"][0]["status"], "truncated")
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {"kernel-dmesg.txt", "manifest.json", "summary.txt"},
        )
        self.assertLessEqual(len((output / "kernel-dmesg.txt").read_bytes()), MAX_LINE_CHARS + 1)
        with self.subTest(item="output path confinement"):
            self.assert_no_output_escaped_to(decoded_directory, sentinel)

    def test_live_kernel_mode_distinguishes_dmesg_failure_from_empty_success(self) -> None:
        cases = (
            ("printf '%s\\n' 'Operation not permitted' >&2\nexit 1", "permission_denied", 1),
            ("exit 7", "error", 7),
            ("exit 0", "empty", 0),
        )
        for index, (body, expected_status, expected_exit_code) in enumerate(cases):
            with self.subTest(status=expected_status):
                env = self.install_live_shims(body)
                output = self.base / f"live-kernel-status-{index}"
                result = self.invoke(
                    "--mode", "kernel", "--output", str(output), env=env
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                manifest = self.manifest(output)
                item = manifest["items"][0]
                self.assertEqual(item["status"], expected_status)
                self.assertEqual(item["command_exit_code"], expected_exit_code)

    def test_missing_essential_utility_is_rejected_before_output_creation(self) -> None:
        env = self.install_live_shims("exit 0")
        env["PATH"] = str(self.bin)
        output = self.base / "missing-awk"
        result = self.invoke(
            "--mode", "kernel", "--output", str(output), env=env
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("awk", result.stderr)
        self.assertFalse(output.exists())

    def test_missing_date_is_recorded_as_a_partial_tool_status(self) -> None:
        self.write_source("proc/version", "Linux fixture\n")
        env = self.restricted_environment(("date",))
        output = self.base / "missing-date"
        result = self.invoke(
            "--mode", "env", "--output", str(output),
            "--source-root", str(self.source), env=env,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.manifest(output)
        self.assertEqual(manifest["collection_status"], "partial")
        clock_item = next(item for item in manifest["items"] if item["name"] == "collector-clock")
        self.assertEqual(clock_item["status"], "tool_missing")

    def test_source_read_failure_is_recorded_as_partial(self) -> None:
        self.write_source("proc/version", "Linux fixture\n")
        env = self.restricted_environment(())
        head_path = self.bin / "head"
        if head_path.exists() or head_path.is_symlink():
            head_path.unlink()
        head_path.write_text("#!/bin/sh\nexit 23\n", encoding="utf-8")
        head_path.chmod(0o755)
        output = self.base / "failed-item-write"

        result = self.invoke(
            "--mode", "env", "--output", str(output),
            "--source-root", str(self.source), env=env,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.manifest(output)
        self.assertEqual(manifest["collection_status"], "partial")
        version_item = next(item for item in manifest["items"] if item["name"] == "proc-version")
        self.assertEqual(version_item["status"], "error")

    def test_output_temp_write_failure_is_nonzero_without_success_claim(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root can write mode-500 output directories")
        env = self.restricted_environment(())
        mkdir_path = self.bin / "mkdir"
        if mkdir_path.exists() or mkdir_path.is_symlink():
            mkdir_path.unlink()
        mkdir_path.write_text(
            "#!/bin/sh\n"
            "/bin/mkdir \"$@\" || exit $?\n"
            "/bin/chmod 500 \"$1\"\n",
            encoding="utf-8",
        )
        mkdir_path.chmod(0o755)
        output = self.base / "unwritable-output"

        result = self.invoke(
            "--mode", "env", "--output", str(output),
            "--source-root", str(self.source), env=env,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("collection_status=", result.stdout)
        self.assertFalse((output / "manifest.json").exists())

    def test_manifest_cat_failure_is_nonzero_and_removes_partial_manifest(self) -> None:
        self.write_source("proc/version", "Linux fixture\n")
        env = self.install_failing_cat(fail_at=1)
        output = self.base / "failed-manifest-write"

        result = self.invoke(
            "--mode", "env", "--output", str(output),
            "--source-root", str(self.source), env=env,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("collection_status=", result.stdout)
        self.assertFalse((output / "manifest.json").exists())

    def test_summary_cat_failure_is_nonzero_and_removes_partial_summary(self) -> None:
        self.write_source("proc/version", "Linux fixture\n")
        env = self.install_failing_cat(fail_at=2)
        output = self.base / "failed-summary-write"

        result = self.invoke(
            "--mode", "env", "--output", str(output),
            "--source-root", str(self.source), env=env,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("collection_status=", result.stdout)
        self.assertTrue((output / "manifest.json").is_file())
        self.assertFalse((output / "summary.txt").exists())

    def test_offline_source_root_cannot_be_the_host_root(self) -> None:
        root_alias = self.base / "root-alias"
        root_alias.symlink_to("/")
        for index, root in enumerate((Path("/"), root_alias)):
            with self.subTest(root=str(root)):
                output = self.base / f"root-source-{index}"
                result = self.invoke(
                    "--mode", "env", "--output", str(output), "--source-root", str(root)
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_offline_process_mode_collects_pid_files_and_mount_context(self) -> None:
        self.write_source("proc/4242/status", "Name:\tworker\nState:\tS (sleeping)\nVmRSS:\t2048 kB\n")
        self.write_source("proc/4242/limits", "Max open files 1024 4096 files\n")
        self.write_source("proc/4242/wchan", "futex_wait_queue\n")
        self.write_source("proc/4242/cgroup", "0::/service.slice/worker.service\n")
        self.write_source("proc/4242/mountinfo", "36 25 0:32 / / rw - rootfs rootfs rw\n")

        result, output = self.collect("process", "process-output", "--pid", "4242")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.manifest(output)["pid"], "4242")
        self.assertIn("worker.service", (output / "process-4242-cgroup.txt").read_text())
        self.assertIn("rootfs", (output / "process-4242-mountinfo.txt").read_text())
        self.assertFalse(self.command_log.exists())

    def test_missing_snapshot_files_are_recorded_as_partial_not_healthy(self) -> None:
        self.write_source("proc/version", "Linux partial-fixture\n")

        result, output = self.collect("env", "partial-output")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.manifest(output)
        self.assertEqual(manifest["collection_status"], "partial")
        statuses = {item["status"] for item in manifest["items"]}
        self.assertIn("missing", statuses)
        summary = (output / "summary.txt").read_text(encoding="utf-8").lower()
        self.assertIn("partial", summary)
        self.assertIn("missing data does not indicate a healthy target", summary)

    def test_unreadable_snapshot_file_has_a_permission_status(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root can read mode-000 fixture files")
        version = self.write_source("proc/version", "Linux private-fixture\n")
        version.chmod(0)

        result, output = self.collect("env", "permission-output")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        items = self.manifest(output)["items"]
        version_item = next(item for item in items if item["name"] == "proc-version")
        self.assertEqual(version_item["status"], "permission_denied")

    def test_pid_is_required_for_process_mode_and_injection_is_rejected(self) -> None:
        missing_pid = self.invoke(
            "--mode", "process", "--output", str(self.base / "missing-pid"),
            "--source-root", str(self.source),
        )
        self.assertNotEqual(missing_pid.returncode, 0)
        self.assertFalse((self.base / "missing-pid").exists())

        for invalid_pid in ("0", "-1", "12/../../etc", "12;touch", "12$(id)"):
            with self.subTest(pid=invalid_pid):
                output = self.base / ("bad-pid-" + str(len(invalid_pid)))
                result = self.invoke(
                    "--mode", "process", "--output", str(output),
                    "--source-root", str(self.source), "--pid", invalid_pid,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_existing_output_and_traversal_are_rejected_without_overwriting(self) -> None:
        existing = self.base / "existing"
        existing.mkdir()
        sentinel = existing / "keep.txt"
        sentinel.write_text("keep me\n", encoding="utf-8")
        result = self.invoke(
            "--mode", "env", "--output", str(existing), "--source-root", str(self.source)
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep me\n")

        escaped = self.base / "escape"
        traversing = str(self.base / "nested" / ".." / "escape")
        traversal_result = self.invoke(
            "--mode", "env", "--output", traversing, "--source-root", str(self.source)
        )
        self.assertNotEqual(traversal_result.returncode, 0)
        self.assertFalse(escaped.exists())

        controlled = str(self.base / "bad\x01path")
        control_result = self.invoke(
            "--mode", "env", "--output", controlled, "--source-root", str(self.source)
        )
        self.assertNotEqual(control_result.returncode, 0)
        self.assertFalse(Path(controlled).exists())

        controlled_root = self.base / "snapshot\x02control"
        controlled_root.mkdir()
        control_root_output = self.base / "control-root-output"
        control_root_result = self.invoke(
            "--mode", "env", "--output", str(control_root_output),
            "--source-root", str(controlled_root),
        )
        self.assertNotEqual(control_root_result.returncode, 0)
        self.assertFalse(control_root_output.exists())

    def test_captured_text_is_bounded_by_bytes_lines_and_width(self) -> None:
        long_lines = "x" * (MAX_LINE_CHARS + 100) + "\n"
        many_lines = "".join(f"line-{i:03d}\n" for i in range(MAX_LINES + 10))
        self.write_source("proc/version", "v" * (MAX_SOURCE_BYTES + 1))
        self.write_source("etc/os-release", "\t" * (MAX_LINE_CHARS + 20) + "\n" + long_lines + many_lines)
        for path, contents in (
            ("proc/cmdline", "cmdline\n"),
            ("proc/meminfo", "MemTotal: 1 kB\n"),
            ("proc/swaps", "Filename Type Size Used Priority\n"),
            ("proc/device-tree/model", b"model\x00"),
            ("proc/device-tree/compatible", b"compatible\x00"),
        ):
            self.write_source(path, contents)

        result, output = self.collect("env", "bounded-output")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        version = (output / "proc-version.txt").read_bytes()
        os_release = (output / "os-release.txt").read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(version), MAX_LINES * (MAX_LINE_CHARS + 1) + 80)
        self.assertLessEqual(len((output / "os-release.txt").read_bytes()), MAX_SOURCE_BYTES)
        self.assertLessEqual(len(os_release), MAX_LINES + 1)
        self.assertTrue(all(len(line) <= MAX_LINE_CHARS for line in os_release))
        statuses = {item["status"] for item in self.manifest(output)["items"]}
        self.assertIn("truncated", statuses)


if __name__ == "__main__":
    unittest.main()
