# Debugging Lessons

Read this ledger before every new debugging, implementation, deployment, or validation phase. Append mistakes and disproved assumptions before continuing.

## Mandatory workflow

1. Read this file before new work.
2. Validate the real user entry point and environment.
3. Record failures and false assumptions before continuing.
4. Declare completion only after end-to-end verification.

## Error records

### E001 Patch cannot delete and add the same path in one request

- **Symptom**: apply_patch rejected an Agent rewrite and a later vendor-note patch before changing any files
- **Cause**: The requests used multiple operations for one path (Delete+Add or duplicate Update File operations)
- **Lesson**: Use a single Update File operation for replacements
- **Prevention check**: Generate one update hunk per existing file and inspect tool exit status

### E002 Multi-hunk documentation patch used stale context

- **Symptom**: Multiple domain-worker patches and asserted replacements, including storage moves and a later display-table edit, were rejected at mismatched surrounding text; the guards prevented partial changes
- **Cause**: The patch grouped edits around guessed exact tail text rather than the current file
- **Lesson**: Read current lines and use smaller verified hunks for independent document corrections
- **Prevention check**: Before editing a section verify its exact contents; after rejection inspect diff before retry. If the same mismatch repeats, construct edits from freshly read text and assert a unique replacement match.

### E003 Time-based benchmark contradicted total-write limit

- **Symptom**: New fio recipe combined --time_based with a claimed 512 MiB total-write cap
- **Cause**: A common duration-based benchmark option repeats the workload and defeats the stated byte bound
- **Lesson**: Distinguish file working-set size, cumulative write volume, I/O runtime and final synchronization time
- **Prevention check**: For a bytes-or-time bounded diagnostic omit --time_based, specify size/io_size/runtime and qualify fsync latency

### E004 Cross-file qualifications were not fully propagated

- **Symptom**: Independent review found stale RK3588 swap/CMA absolutes and universal i.MX plugin claims after main skills had been corrected
- **Cause**: Verification concentrated on entrypoints and did not reconcile every duplicate platform summary
- **Lesson**: A corrected central rule must be checked against platform references and README summaries that repeat it
- **Prevention check**: Search owned reference trees and both READMEs for duplicate swap/OOM/CMA/capability claims, then review their context

### E005 Routing text used a different path base than its links

- **Symptom**: Agent text said package-root relative paths while ../skills links were relative to the Agent file; static link checks still passed
- **Cause**: Markdown resolution and natural-language loader instructions were reviewed separately
- **Lesson**: State the path base at every instruction layer and distinguish selection, body availability and actual loading evidence
- **Prevention check**: Verify Agent links relative to the Agent directory, references relative to SKILL.md, and evaluate actual read paths rather than answer correctness alone

### E006 Repository root was mistaken for plugin root during inspection

- **Symptom**: A routing worker initially read skills/... from repository root and the reads failed
- **Cause**: The expert is nested one directory below the repository root
- **Lesson**: Resolve repository root, expert-package root and instruction-file directory separately
- **Prevention check**: Use verified embedded-software-architect/skills paths and source-relative link bases before reads or replacements

### E007 Framework membership overrode the actual failure layer

- **Symptom**: Draft routing selected Qt whenever a fault occurred inside a Qt app, including protocol or storage failures; a later shorthand also grouped TCP transport with MQTT/TLS application protocols
- **Cause**: The selection predicate used application framework membership instead of the subsystem being diagnosed
- **Lesson**: Route by user objective and concrete evidence; treat the framework or transport as context unless its own behavior is implicated
- **Prevention check**: Include Qt-hosted MQTT/TLS, TCP transport and database-failure counterexamples; Qt selection requires rendering/QPA/scene-graph/UI evidence, while TCP/socket and application-protocol semantics have separate owners

### E008 Follow-up tool received an unsupported dispatch field

- **Symptom**: collaboration.followup_task rejected an extra task_name argument; no message was delivered
- **Cause**: Spawn-task schema was mixed into follow-up-task schema
- **Lesson**: Follow-up accepts only target and message
- **Prevention check**: Check the live tool schema and omit spawn-only fields when resuming an existing worker

### E009 Skill root alias was assumed instead of resolved

- **Symptom**: A worker looked for using-superpowers under .system and the read failed
- **Cause**: It used the system-skill root for a skill cataloged under the user skill root
- **Lesson**: Resolve the catalog alias for the named skill rather than inferring its directory
- **Prevention check**: Use declared r0/r1 mappings and the exact SKILL.md path; scoped subagents skip process skills that explicitly exempt them

### E010 Vendor-note replacement left malformed Markdown structure

- **Symptom**: Draft BSP/vendor-reference edits left unclosed code fences, duplicate table headers and a path note inside a tree-code fence; a storage edit also briefly removed a closing fence. Scoped validation caught and corrected these before integration
- **Cause**: Removing executable recipes did not preserve surrounding Markdown delimiters consistently
- **Lesson**: Treat code-fence and table boundaries as part of the edited unit
- **Prevention check**: Inspect complete surrounding sections and run balanced-fence plus reference checks after moving/removing code blocks

### E011 Collector fixture assertion expected the filename instead of the supplied content

- **Symptom**: Collector fixtures confused a filename with payload, used a non-Linux uname shim before the intended branch, and asserted an incidental human wording variant instead of structured failure behavior
- **Cause**: The assertion confused the output file identity with its sample payload
- **Lesson**: Assert the exact supplied fixture content or relevant fields and separately check the output path
- **Prevention check**: Review fixture inputs and gating conditions before changing behavior; simulate Linux explicitly for live-mode branches and assert structured statuses/exit codes rather than incidental prose wording

### E012 Added patch line lacked its diff prefix

- **Symptom**: A media workflow addition was rejected atomically at an unprefixed gst-inspect command line; a later combined debug-document patch repeated the missing addition-prefix error and was split into smaller hunks
- **Cause**: A new code-fence body line lacked the required addition marker in the patch format
- **Lesson**: Every added line including code-fence content needs the patch addition prefix
- **Prevention check**: Use small complete added-file patches and inspect generated patch syntax before submission

### E013 Frontmatter check assumed an unavailable YAML dependency

- **Symptom**: A worker validation command failed before parsing files because Python PyYAML was not installed
- **Cause**: The environment dependency was assumed rather than checked; prior successful checks used Ruby YAML
- **Lesson**: Distinguish missing validation tooling from invalid content and reuse available parsers without installing unnecessary packages
- **Prevention check**: Use Python standard-library fixture tests and the installed Ruby YAML.safe_load for full frontmatter parsing; note unavailable PyYAML in dispatch context

### E014 Bounded kernel capture lost recent events and producer failure status

- **Symptom**: Draft collector retained the start of dmesg instead of the recent failure tail and treated a failing producer without stderr as empty success
- **Cause**: File-prefix truncation was reused for a command log stream and pipeline status only reflected the final consumer
- **Lesson**: Bound log output while retaining the relevant recent events and preserve producer exit status separately in POSIX shell
- **Prevention check**: Test old-log-plus-recent-Oops input and nonzero producer with/without stderr using deterministic command shims

### E015 Collector manifest and offline boundaries needed explicit preconditions

- **Symptom**: Draft collector could produce malformed metadata with absent mandatory utilities or C0 path bytes, and accepted host root as an offline source
- **Cause**: Serialization dependencies, supported path characters and genuine snapshot-root assumptions were implicit
- **Lesson**: Validate critical utility/path/source prerequisites before creating output, and state directory-based provenance limits
- **Prevention check**: Test missing mandatory utility, control-character path and canonical offline root / rejection without output creation

### E016 Host-side Device Tree example still pointed at host proc

- **Symptom**: Draft BSP wording allowed host-side inspection of an exported target tree but the command still read /proc/device-tree
- **Cause**: Execution context changed without changing the input source path
- **Lesson**: Moving a command to HOST requires an explicitly exported TARGET data path; host proc is never board evidence
- **Prevention check**: Separate TARGET live DT command from HOST exported-tree template and label both input provenance and placeholder replacement

### E017 Generic debug examples retained non-executable placeholders and metric assumptions

- **Symptom**: Content review found shell examples containing literal angle-bracket PID/board placeholders, a fixed thermal_zone0 temperature, and procps-dependent top field parsing; adjacent IPC statements overstated what blocked calls and zombies prove
- **Cause**: General workflow additions did not fully align older examples with the new command and evidence contracts
- **Lesson**: Review the actual example syntax and metric identity, not only the surrounding new policy; blocked calls are observations rather than root-cause proof
- **Prevention check**: Use validated PID/TID variables, explicit HOST/TARGET inputs and recovery prerequisites, identify thermal zone type/units, and qualify tool-specific columns and IPC inference

### E018 Collector reused offline link restrictions and masked report assembly failure

- **Symptom**: Independent review found common live /etc/os-release symlinks rejected; a failing cat shim reproduced exit 0 with complete/empty manifest items while the summary listed seven items
- **Cause**: Offline containment policy was applied to all live paths, and grouped report writes relied on the final printf status rather than each required write/read
- **Lesson**: Keep offline isolation strict while handling standard live layouts narrowly; a report is successful only if all required item/manifest/summary assembly operations succeed
- **Prevention check**: Test manifest assembly read failures and per-item writes, require nonzero failure without success output, and verify constrained live OS-release fallback provenance separately from offline symlink rejection

### E019 GitHub authentication check failed during release preparation

- **Symptom**: Sandboxed gh auth status reported the configured GitHub account token invalid before the repository query could run
- **Cause**: Restricted sandbox access; the same check with permitted host access authenticated successfully through the keyring and confirmed repository ADMIN permission
- **Lesson**: Distinguish sandbox/authentication limitations from repository permission, and do not request or expose access tokens in chat
- **Prevention check**: Retry the read-only credential/repository check with the permitted host access, verify Git transport separately, and keep packaging independent of upload access

### E020 Official WorkBuddy validation requires a marketplace-layout source path

- **Symptom**: The official validator rejected the repository package solely because it was outside the configured my-experts/plugins directory
- **Cause**: The WorkBuddy validator includes installation-location checks even when invoked for packaging
- **Lesson**: A packaging source layout error is distinct from malformed expert content; do not change the user's actual installation to satisfy a release check
- **Prevention check**: Stage an exact payload copy in an isolated temporary WorkBuddy marketplace layout, set WORKBUDDY_CONFIG_DIR only for the validation/packaging subprocess, and verify the extracted archive independently
