# Expert reliability and kernel capability implementation plan

> For agentic workers: use subagent-driven-development with non-overlapping file ownership. Do not commit, push, install, or operate a target board.

**Goal:** Correct the reviewed expert-package defects and add practical Linux driver and kernel guidance.

**Architecture:** Preserve the WorkBuddy Agent package. BSP owns boot/build/Devicetree; a new `linux-device-drivers` skill owns driver lifecycle, synchronization, MMIO/DMA and power management. Existing domain skills retain their names and receive scoped corrections.

**Tech Stack:** Markdown skills and references, JSON plugin metadata, dependency-free Python package validation.

**Spec:** The two review responses and the user's request to correct problems and complete kernel capabilities in this chat.

## Global constraints

- Work in the current repository; preserve unrelated changes. No commits, pushes, installation or live-board operations.
- Preserve the existing plugin identity and WorkBuddy metadata shape. Register `./skills/linux-device-drivers`; the package will contain 13 skills. Keep version 0.1.0 unless a release is requested.
- Chinese instructions; concise, task-routed skills and references. Kernel examples are version-qualified, not claimed as compiled or board-tested.
- Use target kernel source/bindings and primary documentation as authority. Do not invent SoC register values, hardware capabilities or SDK APIs.
- Distinguish host, bootloader and target commands, observations from hypotheses, and local verification from board verification.
- Keep destructive hardware/storage operations out of default diagnostic command sequences. Respect existing user authorization rather than introducing blanket confirmation gates.
- Independent file ownership during implementation. Root owns metadata, both READMEs, the Agent prompt, plan and lessons ledger.

## Task 1: BSP, peripherals and Linux driver skill

**Files:** `embedded-bsp-kernel/**`, `embedded-peripherals/**`, new `linux-device-drivers/**` under `embedded-software-architect/skills/`.

- [x] Record original failures against concrete DTS/matching/build scenarios before editing.
- [x] Correct ARM64 toolchains, DT extraction (`-I fs` for live tree), DT binding examples/IRQ flags/comments, matching/autoloading, and target-version API selection.
- [x] Add staged board bring-up, reproducible kernel/module builds, kernel config/symbol compatibility, target binding checks, and rollback/evidence guidance.
- [x] Add driver lifecycle, deferred probe, devres boundaries, asynchronous teardown, context/locks, MMIO/DMA/IOMMU/cache ownership, PM, subsystem selection, and validation guidance. Put detailed conditional material in focused references and link them.
- [x] Check all added references, examples and primary source links. Report changes and verification limits.

## Task 2: Evidence-driven diagnostics

**Files:** `embedded-perf-debug/**`, `embedded-debug-workflow/**`, `embedded-networking/**` under the skills directory.

- [x] Record baseline failures for cgroup OOM, traced-but-running process, and host-side Oops decoding.
- [x] Replace premature OOM/leak/fragmentation conclusions with hypotheses and evidence branches. Separate peripheral failures from OOM causes.
- [x] Correct TracerPid interpretation, symbolization prerequisites and host/target log transfer; remove rigid one-layer-at-a-time assumptions where direct evidence identifies a lower layer.
- [x] Fix affected shell examples and ambiguous transport diagnostics without rewriting unrelated networking code.
- [x] Verify consistency within owned files and report tests/limits.

## Task 3: Rendering and storage corrections

**Files:** `qt-embedded-rendering/**`, `media-pipeline-linux/**`, `display-compositor-gpu/**`, `data-storage-embedded/**`, `storage-hardware-io/**`, `protocols-embedded/**`, `wireless-connectivity/**` under the skills directory.

- [x] Record baseline failures in software Qt rendering, RenderControl and raw-disk performance testing scenarios.
- [x] Correct Qt backend selection, RenderControl lifecycle and conditional LinuxFB/EGLFS claims.
- [x] Replace default raw-block write benchmarks with bounded file tests; separate array stop/other maintenance operations from read-only diagnostics.
- [x] Correct SQLite SHM/WAL durability and Redis persistence claims using primary documentation.
- [x] Correct repeated no-swap/OOM assertions and malformed command comments in owned files. Qualify unverified SDK examples instead of asserting invented universal capabilities.
- [x] Verify owned file references/examples and report limits.

## Task 4: Package validator and behavior evaluation

**Files:** new `scripts/validate_expert.py`, `tests/test_validate_expert.py`, `tests/expert-scenarios.md`.

- [x] Write fixture-based tests before validator code; cover broken/missing skill registration, unsafe/escaping paths, missing reference, malformed frontmatter, duplicate names, and valid packages. Do not write sentence-matching tests for prose.
- [x] Implement a dependency-free validator for the actual JSON/Markdown package entry point. Report metadata paths, skill names and linked local references; do not claim full WorkBuddy schema/runtime validation.
- [x] Add reusable behavioral scenarios for board unavailable, cgroup OOM, traced-but-running process, Qt software rendering, storage benchmark, deferred probe, async driver teardown and DMA ownership.
- [x] Run tests and the validator; report command output and coverage limits.

## Task 5: Integration and independent review

**Files:** `embedded-software-architect/.codebuddy-plugin/plugin.json`, `embedded-software-architect/agents/embedded-software-architect.md`, both READMEs, plan/ledger.

- [x] Register skill 13 and update count, routing and documentation consistently.
- [x] Put evidence before changes, make verification statuses explicit, remove prechecked board-success template, and allow controlled evidence-driven iteration.
- [x] Replace broad/simple-task skill exemptions with relevance/risk-based routing. Correct platform reference path ambiguity and synchronization/DMA checklist.
- [x] Run fixture tests, package validator and diff whitespace checks. Read every implementation diff.
- [x] Independently evaluate realistic requests using the new instructions without supplying desired answers; compare to original snapshot and document actual observations and limitations.
- [x] Resolve important reviewer findings with the original implementer and re-verify affected checks.
- [x] Deliver concise change summary, file links, checks and unverified WorkBuddy/board behavior.

## Verification evidence

- Root ran `python3 -m unittest discover -s tests -p 'test_*.py' -v`: 18 fixture tests passed. The validator worker separately demonstrated RED before implementation and for the containment regressions.
- `python3 scripts/validate_expert.py embedded-software-architect` passed for 13 skills, 1 agent, the avatar, and 25 local reference relationships after the final platform-reference corrections.
- Ruby's installed `YAML.safe_load` parsed all 14 instruction frontmatters and checked required string fields, names and description limits. The bundled skill quick-validator requires unavailable PyYAML, so this is an independent full-YAML check rather than a claim that its Python command ran.
- `python3 -m py_compile scripts/validate_expert.py tests/test_validate_expert.py` and `git diff --check` passed. Both new fio example blocks passed `bash -n`; no benchmark commands were executed.
- An independent original-package simulation answered four scenarios reasonably despite contradictory/missing source guidance. No baseline behavioral failure or measured improvement is claimed; source corrections are justified by the reviewed examples and primary documentation.
- An independent fresh-context forward simulation used the revised Agent and relevant skills without the plan, prior findings, expected answers or scenario rubric. Root read all eight replies: unavailable board was left pending, memcg and RSS evidence were qualified, tracing was distinguished from stop, asynchronous teardown ordering was considered, streaming DMA ownership was explicit, Qt software selection was correct, disk testing used bounded ordinary files, and deferred probe used driver-core retry. These are single offline simulated answers, not WorkBuddy runtime tests or a statistical evaluation.
- WorkBuddy import/loading, target kernel compilation, DTS/schema checks against a real BSP, vendor SDK tools and board behavior remain unverified. No installation, deployment, commits or pushes were performed.
- Independent final review identified stale RK3588 CMA/swap assertions, a GPU core-count error and unqualified i.MX summaries. The original authors corrected the platform references, root reconciled both READMEs and two adjacent hardware/toolchain labels, and the scoped re-review marked all five finding groups addressed with no new defect in the fix scope. The final package validator passed with 25 local reference relationships.
