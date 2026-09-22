# Evidence snapshots for the OpenCode-aligned task interface proposal

Immutable snapshots of the upstream sources the proposal cites. Retrieved 2026-09-22. Each entry records the upstream identity and the SHA-256 of the snapshot file.

## OpenCode

- Upstream: `anomalyco/opencode`, branch `dev`, commit `fe3f3a41f79ad292cc3c7c629567385a20ec5130` (`sync release versions for v1.18.32`)
- Files: `packages/opencode/src/tool/task.ts`, `packages/opencode/src/tool/task.txt`, `packages/opencode/src/tool/registry.ts`
- SHA-256:
  - `task.ts`: `db09fa5868ad3ecfdd83aa2bb7243f85e9e2cd13d0b19fd6f307f7a337b2b36e`
  - `task.txt`: `220dcf4ad2582dbdaf2b0bbc8b7f5fa78172b1337539ac1c8912f45f2b9e5d46`
  - `registry.ts`: `a8b24a6d58a80c42307e251905dbaa4f25ca0724569b1e531e412da934ab00fe`

## Codex

- Upstream: `openai/codex`, branch `main`, commit `639d2478cc2e16d6ca715952d2e726a3aecc024e`
- File: `codex-rs/core/src/tools/handlers/multi_agents_spec.rs`
- SHA-256: `2562812621dfdef6e3b0efe2dcd69d90a31cba017dfdfc8b29adc16c94f622bd`

## Claude Code

- Upstream: npm package `@anthropic-ai/claude-code` version `2.1.276`
- File: `sdk-tools.d.ts` (package root)
- SHA-256: `7c5689f18dd70cc079bbddd86db1b1e886ecb98a3c19f3317d40148cd9f2f772`

## ZCode

- Upstream: npm package `zcode-app-cli` version `3.12.3-26`, file `package/vendor/zcode.cjs`
- The full bundle is 11438293 bytes, too large to snapshot. This directory stores:
  - `zcode.cjs.sha256`: SHA-256 of the full bundle, `03441ffbcf12fc467fab0a3a3359255e7304695d11a7c20249a58806f5359002`
  - `zcode-agent-tool-excerpt.cjs`: bytes 9205500 to 9210499 (0-based offsets into the full bundle). The excerpt contains the `Agent` tool metadata block (`metadata:{name:"Agent"...}`) and the Claude Code-compatible `Task` alias block. Verify by re-downloading the tarball from `https://registry.npmjs.org/zcode-app-cli/-/zcode-app-cli-3.12.3-26.tgz`, checking the bundle SHA-256, and reading the recorded byte range.
- SHA-256 of the excerpt: `dfa82f741ffe34d2db2b83a81c1e372aecbf3373d07743b6c53117ea5ab025be`

## Recorded-machine transcripts

Two directories under this manifest hold transcripts recorded on this machine rather than upstream snapshots. Each transcript self-documents its capture date, tool versions, working directory, commands, complete output, and exit codes:

- `tau-capability/transcript.txt`: Tau CLI session capabilities (pinned session ids, `--session-role subagent` hiding, resume stream, `Unknown session:` failure)
- `baseline-tests/transcript.txt`: the extension test suite run at baseline commit `b833ebd` (267 tests, all passing)
