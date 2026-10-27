"""Mechanical safety checks for executable shell examples in diagnostic docs."""

from __future__ import annotations

import re
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    ROOT / "embedded-software-architect/skills/embedded-debug-workflow/SKILL.md",
    ROOT / "embedded-software-architect/skills/embedded-debug-workflow/references/debug-playbook.md",
    ROOT / "embedded-software-architect/skills/embedded-debug-workflow/references/process-sampling.md",
    ROOT / "embedded-software-architect/skills/embedded-perf-debug/SKILL.md",
    ROOT / "embedded-software-architect/skills/embedded-perf-debug/references/forensics-cheatsheet.md",
)
SHELL_FENCE = re.compile(
    r"(?ms)^```(?P<language>bash|sh|shell)(?:[ \t].*)?\r?\n(?P<body>.*?)^```[ \t]*$"
)
UNRESOLVED_TARGET_ID = re.compile(r"<\s*(?:pid|tid|board)\s*>", re.IGNORECASE)


def shell_blocks(document: Path) -> list[tuple[str, str]]:
    text = document.read_text(encoding="utf-8")
    return [
        (match.group("language"), match.group("body"))
        for match in SHELL_FENCE.finditer(text)
    ]


class DiagnosticExampleSafetyTests(unittest.TestCase):
    def test_shell_examples_do_not_use_unresolved_target_ids(self) -> None:
        """Executable snippets must use validated values instead of angle-bracket IDs."""
        for document in DOCUMENTS:
            blocks = shell_blocks(document)
            for block_number, (_language, block) in enumerate(blocks, start=1):
                match = UNRESOLVED_TARGET_ID.search(block)
                if match:
                    self.fail(
                        f"{document.relative_to(ROOT)} shell block {block_number} "
                        f"contains unresolved target placeholder {match.group(0)!r}"
                    )

    def test_complete_shell_examples_parse_without_execution(self) -> None:
        """Parse complete fenced examples only; target commands are never run."""
        for document in DOCUMENTS:
            for block_number, (language, block) in enumerate(shell_blocks(document), start=1):
                # Parse with the declared shell and Bash as an independent parser for
                # nested command substitutions; neither command evaluates the block.
                parsers = ("bash", "sh") if language == "bash" else ("sh", "bash")
                for shell in parsers:
                    result = subprocess.run(
                        [shell, "-n"],
                        input=block,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        f"{document.relative_to(ROOT)} shell block {block_number} "
                        f"does not parse with {shell}:\n{result.stderr}",
                    )

    def test_invalid_target_pid_fails_without_waiting_for_stdin(self) -> None:
        """The sampler must use caller-provided TARGET_PID instead of prompting."""
        sampling_doc = (
            ROOT
            / "embedded-software-architect/skills/embedded-debug-workflow/references/process-sampling.md"
        )
        setup_block = shell_blocks(sampling_doc)[0][1]
        id_validation = setup_block.index('if ! is_positive_decimal_id "$candidate_pid"')
        first_proc_path = setup_block.index("/proc/")
        self.assertLess(
            id_validation,
            first_proc_path,
            "reject non-decimal input before forming any /proc path",
        )
        child_env = os.environ.copy()
        child_env["TARGET_PID"] = "not-a-positive-decimal-id"
        child_env.pop("TARGET_TID", None)
        process = subprocess.Popen(
            ["sh", "-c", setup_block],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=child_env,
        )
        timed_out = False
        returncode = None
        try:
            try:
                returncode = process.wait(timeout=0.75)
            except subprocess.TimeoutExpired:
                timed_out = True
        finally:
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate(timeout=2)

        self.assertFalse(
            timed_out,
            "invalid TARGET_PID must be rejected without waiting for stdin",
        )
        self.assertEqual(returncode, 2, f"unexpected setup result: {stdout} {stderr}")


if __name__ == "__main__":
    unittest.main()
