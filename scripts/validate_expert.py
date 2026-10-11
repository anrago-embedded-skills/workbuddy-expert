#!/usr/bin/env python3
"""Check package paths, registered skills, frontmatter, and local Markdown links."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit


METADATA_RELATIVE_PATH = Path(".codebuddy-plugin") / "plugin.json"
FRONTMATTER_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$")
INLINE_CODE_SPAN = re.compile(r"(?<!`) (`+)(.+?)\1(?!`)", re.DOTALL | re.VERBOSE)
INLINE_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))")
REFERENCE_DEFINITION = re.compile(r"^\s*\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))", re.MULTILINE)
INLINE_MD_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:\.{1,2}/)?(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.md"
    r"(?:#[A-Za-z0-9_.:-]+)?)",
    re.IGNORECASE,
)
GENERIC_MD_NAMES = {
    "bar.md",
    "baz.md",
    "example.md",
    "file.md",
    "filename.md",
    "foo.md",
    "sample.md",
    "target.md",
}
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
NUMERIC_SCALAR = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


class PackageValidator:
    def __init__(self, package: Path) -> None:
        self.package_argument = package
        self.package = package.resolve()
        self.errors: list[str] = []
        self.inventory: list[str] = []
        self.local_references: set[tuple[Path, Path]] = set()
        self.registered_skill_dirs: set[Path] = set()
        self.registered_paths: dict[Path, str] = {}
        self._skill_names: dict[str, Path] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def run(self) -> bool:
        if not self.package.is_dir():
            self.error(f"package path is not a directory: {self.package_argument}")
            return False

        metadata_path = self._contained_path(self.package / METADATA_RELATIVE_PATH, "metadata")
        if metadata_path is None:
            return False
        metadata = self._read_metadata(metadata_path)
        if metadata is None:
            return False

        agents = self._registered_list(metadata, "agents")
        skills = self._registered_list(metadata, "skills")
        avatar = self._registered_string(metadata, "avatar")

        for entry in agents:
            path = self._registered_path(entry, "agent", "file")
            if path is not None:
                self.inventory.append(f"Agent: {self._display(path)}")
                self._collect_markdown(path)

        for entry in skills:
            path = self._registered_path(entry, "skill", "directory")
            if path is not None:
                self.registered_skill_dirs.add(path)
                self.inventory.append(f"Skill path: {self._display(path)}")
                skill_file = self._contained_path(path / "SKILL.md", "skill SKILL.md")
                if skill_file is None:
                    continue
                if not skill_file.is_file():
                    self.error(f"registered skill is missing SKILL.md: {self._display(path)}")
                    continue
                self._validate_skill_frontmatter(skill_file)
                self._collect_markdown_tree(path)

        if avatar is not None:
            path = self._registered_path(avatar, "avatar", "file")
            if path is not None:
                self.inventory.append(f"Avatar: {self._display(path)}")

        self._check_actual_skill_registration()
        self._check_local_references()
        self._check_reference_reachability()
        return not self.errors

    def _read_metadata(self, path: Path) -> dict[str, object] | None:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.error(f"cannot read metadata {self._display(path)}: {exc.strerror or exc}")
            return None
        except UnicodeError as exc:
            self.error(f"metadata is not UTF-8 ({self._display(path)}): {exc}")
            return None

        try:
            metadata = json.loads(content)
        except json.JSONDecodeError as exc:
            self.error(
                f"invalid JSON in {self._display(path)} at line {exc.lineno}, column {exc.colno}: "
                f"{exc.msg}"
            )
            return None
        if not isinstance(metadata, dict):
            self.error(f"metadata must be a JSON object: {self._display(path)}")
            return None
        return metadata

    def _registered_list(self, metadata: dict[str, object], key: str) -> list[str]:
        value = metadata.get(key)
        if not isinstance(value, list):
            self.error(f"metadata field '{key}' must be a list of paths")
            return []
        result: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                self.error(f"metadata field '{key}' item {index + 1} must be a non-empty path")
            else:
                result.append(item)
        return result

    def _registered_string(self, metadata: dict[str, object], key: str) -> str | None:
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip():
            self.error(f"metadata field '{key}' must be a non-empty path")
            return None
        return value

    def _registered_path(self, raw: str, label: str, expected: str) -> Path | None:
        normalized = raw.strip()
        posix = Path(normalized)
        windows = PureWindowsPath(normalized)
        if (
            posix.is_absolute()
            or windows.is_absolute()
            or bool(windows.drive)
            or "\\" in normalized
            or "\x00" in normalized
            or ".." in posix.parts
            or ".." in windows.parts
        ):
            self.error(f"unsafe {label} path '{raw}': paths must stay inside the package")
            return None

        candidate = self.package / posix
        resolved = self._contained_path(candidate, label, raw=raw)
        if resolved is None:
            return None

        if resolved in self.registered_paths:
            previous = self.registered_paths[resolved]
            self.error(
                f"duplicate registered path '{self._display(resolved)}' "
                f"({previous} and {label})"
            )
        else:
            self.registered_paths[resolved] = label

        if expected == "directory" and not resolved.is_dir():
            self.error(f"registered {label} path is not an existing directory: {raw}")
            return None
        if expected == "file" and not resolved.is_file():
            self.error(f"registered {label} path is not an existing file: {raw}")
            return None
        return resolved

    def _contained_path(self, path: Path, label: str, raw: str | None = None) -> Path | None:
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError) as exc:
            display = raw if raw is not None else self._display_without_resolve(path)
            self.error(f"cannot resolve {label} path '{display}': {exc}")
            return None
        if not resolved.is_relative_to(self.package):
            display = raw if raw is not None else self._display_without_resolve(path)
            self.error(f"unsafe {label} path '{display}': resolved path escapes the package")
            return None
        return resolved

    def _validate_skill_frontmatter(self, path: Path) -> None:
        contained = self._contained_path(path, "skill SKILL.md")
        if contained is None:
            return
        path = contained
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.error(f"cannot read skill file {self._display(path)}: {exc.strerror or exc}")
            return
        except UnicodeError as exc:
            self.error(f"skill file is not UTF-8 ({self._display(path)}): {exc}")
            return

        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            self.error(f"missing YAML frontmatter in {self._display(path)}")
            return

        end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
        if end is None:
            self.error(f"unterminated YAML frontmatter in {self._display(path)}")
            return

        fields: dict[str, str] = {}
        for index, line in enumerate(lines[1:end], start=1):
            match = FRONTMATTER_FIELD.match(line)
            if not match:
                continue
            key, value = match.groups()
            key = key.lower()
            if key not in {"name", "description"}:
                continue
            if key in fields:
                self.error(f"duplicate frontmatter field '{key}' in {self._display(path)}")
                continue
            parsed = self._frontmatter_scalar(value, lines, index, end)
            if parsed is None:
                self.error(
                    f"frontmatter field '{key}' must use a supported string scalar "
                    f"in {self._display(path)}"
                )
                parsed = ""
            fields[key] = parsed

        for required in ("name", "description"):
            if not fields.get(required, "").strip():
                self.error(f"frontmatter requires a non-empty '{required}' in {self._display(path)}")

        name = fields.get("name", "").strip()
        if name and not SKILL_NAME.fullmatch(name):
            self.error(
                f"skill name '{name}' must use lowercase letters, digits, and hyphens "
                f"in {self._display(path)}"
            )
        if name and name != path.parent.name:
            self.error(
                f"skill name '{name}' does not match folder '{path.parent.name}' "
                f"in {self._display(path)}"
            )
        if name:
            prior = self._skill_names.get(name)
            if prior is not None and prior != path.parent:
                self.error(
                    f"duplicate skill name '{name}' in {self._display(prior / 'SKILL.md')} "
                    f"and {self._display(path)}"
                )
            self._skill_names.setdefault(name, path.parent)
            self.inventory.append(f"Skill name: {name}")

    @staticmethod
    def _frontmatter_scalar(value: str, lines: list[str], index: int, end: int) -> str | None:
        value = value.strip()
        if value in {"|", ">", "|-", ">-", "|+", ">+"}:
            block = []
            for line in lines[index + 1 : end]:
                if line and not line[0].isspace():
                    break
                if line.strip():
                    block.append(line.strip())
            return " ".join(block)
        if not value or value.startswith("#"):
            return ""
        if value[0] in "\"'":
            if len(value) < 2 or value[-1] != value[0]:
                return None
            if value[0] == '"':
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, str) else None
            inner = value[1:-1]
            if re.search(r"(?<!')'(?!')", inner):
                return None
            return inner.replace("''", "'")
        if value[0] in "[{" or value.lower() in {"null", "~", "true", "false"}:
            return None
        if NUMERIC_SCALAR.fullmatch(value):
            return None
        value = re.sub(r"\s+#.*$", "", value).strip()
        return value

    def _check_actual_skill_registration(self) -> None:
        skills_root = self.package / "skills"
        if not skills_root.is_dir():
            return
        actual: set[Path] = set()
        for skill_file in skills_root.rglob("SKILL.md"):
            resolved = skill_file.parent.resolve()
            if resolved.is_relative_to(self.package):
                actual.add(resolved)
        for path in sorted(actual - self.registered_skill_dirs):
            self.error(f"actual skill is not registered: {self._display(path)}")

    def _collect_markdown_tree(self, directory: Path) -> None:
        for path in directory.rglob("*.md"):
            resolved = path.resolve()
            if resolved.is_file() and resolved.is_relative_to(self.package):
                self._collect_markdown(resolved)

    def _collect_markdown(self, path: Path) -> None:
        if path.suffix.lower() != ".md" or not path.is_file():
            return
        contained = self._contained_path(path, "Markdown file")
        if contained is None:
            return
        path = contained
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self.error(f"cannot read Markdown file {self._display(path)}: {exc}")
            return

        body = self._without_fenced_code(content)
        targets: set[str] = set()
        for match in INLINE_MARKDOWN_LINK.finditer(body):
            targets.add(match.group(1) or match.group(2))
        for match in REFERENCE_DEFINITION.finditer(body):
            targets.add(match.group(1) or match.group(2))

        for target in targets:
            self._consider_reference(path, target, "Markdown link")

        for code_match in INLINE_CODE_SPAN.finditer(body):
            inline_content = code_match.group(2)
            for token_match in INLINE_MD_TOKEN.finditer(inline_content):
                token = token_match.group(1)
                before = inline_content[: token_match.start(1)]
                after = inline_content[token_match.end(1) :]
                if (before.endswith("<") and after.startswith(">")) or "\\" in token:
                    continue
                if self._looks_like_generic_example(token):
                    continue
                self._consider_reference(path, token, "inline-code reference")

    @staticmethod
    def _without_fenced_code(content: str) -> str:
        kept: list[str] = []
        fence_char: str | None = None
        fence_length = 0
        for line in content.splitlines():
            stripped = line.lstrip()
            marker = stripped[:3]
            if fence_char is None and marker in {"```", "~~~"}:
                fence_char = marker[0]
                fence_length = len(stripped) - len(stripped.lstrip(fence_char))
                continue
            if fence_char is not None:
                closing_length = len(stripped) - len(stripped.lstrip(fence_char))
                if closing_length >= fence_length and stripped[closing_length:].strip() == "":
                    fence_char = None
                    fence_length = 0
                continue
            kept.append(line)
        return "\n".join(kept)

    @staticmethod
    def _looks_like_generic_example(target: str) -> bool:
        decoded = unquote(target)
        path = decoded.split("#", 1)[0]
        lowered = path.lower()
        if any(marker in path for marker in ("<", ">", "{", "}", "...")):
            return True
        parts = lowered.replace("\\", "/").split("/")
        if lowered in GENERIC_MD_NAMES:
            return True
        return len(parts) >= 3 and parts[0:2] == ["path", "to"] and parts[-1] in GENERIC_MD_NAMES

    def _consider_reference(self, source: Path, target: str, context: str) -> None:
        target = target.strip().strip("\"'")
        if not target or self._looks_like_generic_example(target):
            return
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or target.startswith("//"):
            return
        if target.startswith("/") or "\\" in parsed.path:
            return
        local_path = unquote(parsed.path)
        if context == "Markdown link" and local_path.lower().endswith(".sh"):
            candidate = self._contained_path(
                source.parent / local_path, "local shell helper", raw=target
            )
            if candidate is not None and not candidate.is_file():
                self.error(
                    f"missing local shell helper in {self._display(source)}: {target}"
                )
            return
        if not local_path.lower().endswith(".md"):
            return
        candidate = self._contained_path(
            source.parent / local_path, "local Markdown reference", raw=target
        )
        if candidate is None:
            return
        self.local_references.add((source, candidate))
        if not candidate.is_file():
            self.error(
                f"missing local Markdown reference in {self._display(source)}: "
                f"{target} ({context})"
            )

    def _check_local_references(self) -> None:
        for target in sorted({target for _, target in self.local_references}, key=str):
            self.inventory.append(f"Local Markdown reference: {self._display(target)}")

    def _check_reference_reachability(self) -> None:
        for skill_dir in sorted(self.registered_skill_dirs, key=str):
            references_dir = skill_dir / "references"
            if not references_dir.exists() and not references_dir.is_symlink():
                continue
            contained_references_dir = self._contained_path(
                references_dir, "skill references directory"
            )
            if contained_references_dir is None:
                continue
            if not contained_references_dir.is_relative_to(skill_dir):
                self.error(
                    f"unsafe skill references directory {self._display(references_dir)}: "
                    "resolved path escapes the skill directory"
                )
                continue
            if not contained_references_dir.is_dir():
                self.error(
                    f"skill references path is not a directory: {self._display(references_dir)}"
                )
                continue

            skill_entry = self._contained_path(skill_dir / "SKILL.md", "skill entrypoint")
            if skill_entry is None:
                continue
            if not skill_entry.is_relative_to(skill_dir):
                self.error(
                    f"unsafe skill entrypoint {self._display(skill_dir / 'SKILL.md')}: "
                    "resolved path escapes the skill directory"
                )
                continue

            reference_files: set[Path] = set()
            for reference_path in contained_references_dir.rglob("*.md"):
                reference_file = self._contained_path(reference_path, "skill reference")
                if reference_file is None:
                    continue
                if not reference_file.is_relative_to(skill_dir):
                    self.error(
                        f"unsafe skill reference {self._display(reference_path)}: "
                        "resolved path escapes the skill directory"
                    )
                    continue
                if not reference_file.is_file():
                    self.error(f"skill reference is not a file: {self._display(reference_path)}")
                    continue
                reference_files.add(reference_file)

            adjacency: dict[Path, set[Path]] = {}
            for source, target in self.local_references:
                if source.is_relative_to(skill_dir) and target.is_relative_to(skill_dir):
                    adjacency.setdefault(source, set()).add(target)

            reachable: set[Path] = set()
            pending = [skill_entry]
            while pending:
                source = pending.pop()
                if source in reachable:
                    continue
                reachable.add(source)
                pending.extend(adjacency.get(source, set()) - reachable)

            for reference_file in sorted(reference_files - reachable, key=str):
                self.error(
                    f"unreachable skill reference in {self._display(skill_dir)}: "
                    f"{self._display(reference_file)}"
                )

    def _display(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.package).as_posix()
        except ValueError:
            return str(path)

    @staticmethod
    def _display_without_resolve(path: Path) -> str:
        return path.as_posix()

    def report(self, passed: bool) -> None:
        print(f"Package: {self.package}")
        print(f"Metadata: {METADATA_RELATIVE_PATH.as_posix()}")
        for entry in self.inventory:
            print(entry)
        unique_target_files = {
            target for _, target in self.local_references if target.is_file()
        }
        print(
            f"Local Markdown reference relationships checked: {len(self.local_references)}; "
            f"unique target files: {len(unique_target_files)}"
        )
        if self.errors:
            for error in self.errors:
                print(f"ERROR: {error}", file=sys.stderr)
        if passed:
            print("Validation passed.")
        else:
            print("Validation failed.", file=sys.stderr)
        print(
            "Static package checks only; required frontmatter string fields are checked "
            "without full YAML parsing. This does not establish WorkBuddy runtime/schema "
            "validity or technical correctness of skill guidance."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate registered package paths, skill metadata, registration coverage, "
            "and local Markdown references."
        )
    )
    parser.add_argument(
        "package",
        nargs="?",
        type=Path,
        default=Path("embedded-software-architect"),
        help="expert package directory (default: embedded-software-architect)",
    )
    arguments = parser.parse_args(argv)
    validator = PackageValidator(arguments.package)
    passed = validator.run()
    validator.report(passed)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
