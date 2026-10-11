"""Behavioral tests for the embedded expert package validator CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_expert.py"


class ExpertPackageValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.base = Path(self.tempdir.name)
        self.package = self.base / "embedded-software-architect"
        self.package.mkdir()
        self.make_package(self.package)

    def make_package(self, package: Path, skill_names: tuple[str, ...] = ("alpha",)) -> None:
        (package / "agents").mkdir(exist_ok=True)
        (package / "avatars").mkdir(exist_ok=True)
        (package / "skills").mkdir(exist_ok=True)
        (package / "agents" / "expert.md").write_text(
            "# Agent\n\nSee [the guide](../skills/alpha/SKILL.md#overview).\n",
            encoding="utf-8",
        )
        (package / "avatars" / "expert.png").write_bytes(b"fixture image")
        skills = []
        for name in skill_names:
            folder = package / "skills" / name
            (folder / "references").mkdir(parents=True, exist_ok=True)
            (folder / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: A fixture skill.\n---\n"
                "# Overview\n\n"
                "See [the reference](references/guide.md#details) and "
                "`references/guide.md#details`.\n\n"
                "External [docs](https://example.com/docs.md), `path/to/file.md`, "
                "and `<target>.md` are examples, not package links.\n",
                encoding="utf-8",
            )
            (folder / "references" / "guide.md").write_text(
                "# Details\n\nA real local reference.\n", encoding="utf-8"
            )
            skills.append(f"./skills/{name}")
        metadata = {
            "name": "fixture-expert",
            "agents": ["./agents/expert.md"],
            "avatar": "avatars/expert.png",
            "skills": skills,
        }
        (package / ".codebuddy-plugin").mkdir(exist_ok=True)
        (package / ".codebuddy-plugin" / "plugin.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

    def invoke(self, package: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VALIDATOR)]
        if package is not None:
            command.append(str(package))
        return subprocess.run(
            command,
            cwd=self.base,
            text=True,
            capture_output=True,
            check=False,
        )

    def metadata(self) -> dict[str, object]:
        path = self.package / ".codebuddy-plugin" / "plugin.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def save_metadata(self, metadata: dict[str, object]) -> None:
        path = self.package / ".codebuddy-plugin" / "plugin.json"
        path.write_text(json.dumps(metadata), encoding="utf-8")

    def test_valid_package_resolves_local_links_and_reports_registered_entries(self) -> None:
        result = self.invoke(self.package)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout
        self.assertIn("agents/expert.md", output)
        self.assertIn("avatars/expert.png", output)
        self.assertIn("alpha", output)
        self.assertIn("references/guide.md", output)

    def test_unlinked_reference_file_fails_validation(self) -> None:
        orphan = self.package / "skills" / "alpha" / "references" / "orphan.md"
        orphan.write_text("# Unlinked reference\n", encoding="utf-8")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("unreachable", output.lower())
        self.assertIn("skills/alpha/references/orphan.md", output)

    def test_linked_local_shell_helper_is_checked_without_execution(self) -> None:
        scripts = self.package / "skills" / "alpha" / "scripts"
        scripts.mkdir()
        helper = scripts / "collect-evidence.sh"
        helper.write_text(
            '#!/bin/sh\ntouch "$(dirname "$0")/executed-marker"\nexit 97\n',
            encoding="utf-8",
        )
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        with skill.open("a", encoding="utf-8") as skill_file:
            skill_file.write("\n[collector](scripts/collect-evidence.sh)\n")

        result = self.invoke(self.package)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((scripts / "executed-marker").exists())

    def test_missing_linked_local_shell_helper_fails_validation(self) -> None:
        scripts = self.package / "skills" / "alpha" / "scripts"
        scripts.mkdir()
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        with skill.open("a", encoding="utf-8") as skill_file:
            skill_file.write("\n[collector](scripts/missing.sh)\n")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("missing local shell helper", output.lower())
        self.assertIn("scripts/missing.sh", output)

    def test_linked_shell_helper_symlink_cannot_escape_package(self) -> None:
        outside = self.base / "outside-helper.sh"
        outside.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        scripts = self.package / "skills" / "alpha" / "scripts"
        scripts.mkdir()
        (scripts / "escape.sh").symlink_to(outside)
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        with skill.open("a", encoding="utf-8") as skill_file:
            skill_file.write("\n[collector](scripts/escape.sh)\n")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe", (result.stdout + result.stderr).lower())

    def test_reference_linked_through_another_reference_is_reachable(self) -> None:
        skill = self.package / "skills" / "alpha"
        guide = skill / "references" / "guide.md"
        detail = skill / "references" / "detail.md"
        appendix = skill / "references" / "nested" / "appendix.md"
        appendix.parent.mkdir()
        guide.write_text("# Guide\n\nContinue to [detail](detail.md).\n", encoding="utf-8")
        detail.write_text(
            "# Detail\n\nContinue to [appendix](nested/appendix.md).\n", encoding="utf-8"
        )
        appendix.write_text("# Appendix\n\nTransitive reference content.\n", encoding="utf-8")

        result = self.invoke(self.package)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("references/detail.md", result.stdout)

    def test_inline_code_reference_can_complete_transitive_path(self) -> None:
        skill = self.package / "skills" / "alpha"
        guide = skill / "references" / "guide.md"
        detail = skill / "references" / "detail.md"
        guide.write_text("# Guide\n\nContinue with `detail.md`.\n", encoding="utf-8")
        detail.write_text("# Detail\n\nTransitive reference content.\n", encoding="utf-8")

        result = self.invoke(self.package)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("references/detail.md", result.stdout)

    def test_link_from_another_skill_does_not_make_reference_reachable(self) -> None:
        self.make_package(self.package, ("alpha", "beta"))
        alpha = self.package / "skills" / "alpha"
        orphan = alpha / "references" / "orphan.md"
        orphan.write_text("# Alpha-only reference\n", encoding="utf-8")
        with (alpha / "SKILL.md").open("a", encoding="utf-8") as skill_file:
            skill_file.write("\nSee [beta guide](../beta/references/guide.md).\n")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("unreachable", output.lower())
        self.assertIn("skills/alpha/references/orphan.md", output)

    def test_reference_symlink_cannot_escape_package(self) -> None:
        outside = self.base / "outside.md"
        outside.write_text("# Outside reference\n", encoding="utf-8")
        escape = self.package / "skills" / "alpha" / "references" / "escape.md"
        escape.symlink_to(outside)

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe", (result.stdout + result.stderr).lower())

    def test_references_directory_symlink_cannot_escape_package(self) -> None:
        skill = self.package / "skills" / "alpha"
        references = skill / "references"
        outside = self.base / "outside-references"
        outside.mkdir()
        references.rename(skill / "references-backup")
        references.symlink_to(outside, target_is_directory=True)
        (skill / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: A fixture skill.\n---\n# Overview\n",
            encoding="utf-8",
        )

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe", (result.stdout + result.stderr).lower())

    def test_report_separates_link_relationships_from_unique_target_files(self) -> None:
        skill = self.package / "skills" / "alpha"
        guide = skill / "references" / "guide.md"
        detail = skill / "references" / "detail.md"
        guide.write_text("# Guide\n\nSee [detail](detail.md).\n", encoding="utf-8")
        detail.write_text("# Detail\n\nBack to [guide](guide.md).\n", encoding="utf-8")

        result = self.invoke(self.package)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "Local Markdown reference relationships checked: 4; unique target files: 3",
            result.stdout,
        )

    def test_package_path_defaults_to_embedded_software_architect(self) -> None:
        result = self.invoke()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("embedded-software-architect", result.stdout)

    def test_every_skill_directory_with_skill_markdown_must_be_registered(self) -> None:
        unregistered = self.package / "skills" / "beta"
        unregistered.mkdir()
        (unregistered / "SKILL.md").write_text(
            "---\nname: beta\ndescription: Another skill.\n---\n", encoding="utf-8"
        )

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta", result.stdout + result.stderr)

    def test_registered_skill_without_skill_markdown_fails(self) -> None:
        (self.package / "skills" / "alpha" / "SKILL.md").unlink()

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SKILL.md", result.stdout + result.stderr)

    def test_skill_markdown_symlink_cannot_escape_package(self) -> None:
        skill_file = self.package / "skills" / "alpha" / "SKILL.md"
        outside_skill = self.base / "outside-SKILL.md"
        outside_skill.write_text(
            "---\nname: alpha\ndescription: Outside file.\n---\n", encoding="utf-8"
        )
        skill_file.unlink()
        skill_file.symlink_to(outside_skill)
        (self.package / "agents" / "expert.md").write_text("# Agent\n", encoding="utf-8")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escape", (result.stdout + result.stderr).lower())

    def test_missing_registered_skill_directory_fails(self) -> None:
        metadata = self.metadata()
        metadata["skills"] = ["./skills/absent"]
        self.save_metadata(metadata)

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/absent", result.stdout + result.stderr)

    def test_invalid_plugin_json_fails_cleanly(self) -> None:
        path = self.package / ".codebuddy-plugin" / "plugin.json"
        path.write_text('{"agents": [}', encoding="utf-8")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugin.json", result.stdout + result.stderr)

    def test_plugin_metadata_symlink_cannot_escape_package(self) -> None:
        metadata_path = self.package / ".codebuddy-plugin" / "plugin.json"
        outside_metadata = self.base / "outside-plugin.json"
        outside_metadata.write_text(json.dumps(self.metadata()), encoding="utf-8")
        metadata_path.unlink()
        metadata_path.symlink_to(outside_metadata)

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escape", (result.stdout + result.stderr).lower())

    def test_non_list_skill_registration_is_reported(self) -> None:
        metadata = self.metadata()
        metadata["skills"] = "./skills/alpha"
        self.save_metadata(metadata)

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills", result.stdout + result.stderr)

    def test_normalized_duplicate_registered_skill_paths_fail(self) -> None:
        metadata = self.metadata()
        metadata["skills"] = ["./skills/alpha", "skills/alpha"]
        self.save_metadata(metadata)

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("duplicate", output.lower())
        self.assertIn("skills/alpha", output)

    def test_duplicate_frontmatter_skill_names_fail(self) -> None:
        self.make_package(self.package, ("alpha", "beta"))
        beta_skill = self.package / "skills" / "beta" / "SKILL.md"
        beta_skill.write_text(
            "---\nname: alpha\ndescription: Conflicting name.\n---\n", encoding="utf-8"
        )

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate", (result.stdout + result.stderr).lower())

    def test_skill_frontmatter_requires_name_description_and_matching_folder(self) -> None:
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        skill.write_text("---\nname: wrong-folder\n---\n", encoding="utf-8")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("description", output.lower())
        self.assertIn("wrong-folder", output)

    def test_missing_frontmatter_delimiter_fails(self) -> None:
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        skill.write_text("name: alpha\ndescription: Missing delimiters.\n", encoding="utf-8")

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frontmatter", (result.stdout + result.stderr).lower())

    def test_unsupported_frontmatter_scalar_forms_fail(self) -> None:
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        skill.write_text(
            '---\nname: "alpha\ndescription: [not a string]\n---\n', encoding="utf-8"
        )

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scalar", (result.stdout + result.stderr).lower())

    def test_skill_name_must_use_lowercase_hyphenated_folder_name(self) -> None:
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        skill.write_text(
            "---\nname: Alpha_1\ndescription: Invalid identifier.\n---\n", encoding="utf-8"
        )

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lowercase", (result.stdout + result.stderr).lower())

    def test_missing_normal_and_inline_code_markdown_references_fail(self) -> None:
        skill = self.package / "skills" / "alpha" / "SKILL.md"
        skill.write_text(
            "---\nname: alpha\ndescription: References.\n---\n"
            "[normal](references/missing.md#section) and `references/also-missing.md`.\n",
            encoding="utf-8",
        )

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("references/missing.md", output)
        self.assertIn("references/also-missing.md", output)

    def test_absolute_and_traversal_registration_paths_are_rejected(self) -> None:
        for unsafe_path in ("/tmp/outside-agent.md", "../outside-agent.md"):
            with self.subTest(path=unsafe_path):
                metadata = self.metadata()
                metadata["agents"] = [unsafe_path]
                self.save_metadata(metadata)

                result = self.invoke(self.package)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsafe", (result.stdout + result.stderr).lower())

    def test_symlink_escape_in_registered_avatar_is_rejected(self) -> None:
        outside = self.base / "outside.png"
        outside.write_bytes(b"outside")
        link = self.package / "avatars" / "escape.png"
        link.symlink_to(outside)
        metadata = self.metadata()
        metadata["avatar"] = "avatars/escape.png"
        self.save_metadata(metadata)

        result = self.invoke(self.package)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
