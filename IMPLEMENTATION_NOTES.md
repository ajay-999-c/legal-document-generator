# Phase 1 implementation notes

Implemented 23 September 2026 against the regenerated FORM_SPEC.md (55 inputs, 51 required, 4 optional). The existing source projects were inspected as references and remain separate; no runtime dependency or import path reaches them.

## Checklist and inventory

- [x] Read dir_tree.md, the Phase 1 plan, regenerated Form specification and legacy generators, UI/validation, configuration/Sheets/processor code and relevant tests/documentation.
- [x] Verify exact new template names and XML placeholders, including run splits, tables and Word headers/footers.
- [x] Create the isolated project `.venv`, requirements and local ignore rules.
- [x] Implement typed configuration, registry and three document adapters.
- [x] Implement strict rendering, text/date validation and atomic local save.
- [x] Implement exact Sheets access, sequential processing, safe CLI and structured outcomes.
- [x] Run offline tests, dependency checks and standalone-copy checks.
- [x] Document designated-row Mac live acceptance commands.
- [x] Run live read-only checks with the user-provided credential file and spreadsheet ID.
- [x] Generate the three explicitly approved live test rows and verify saved ZIP/XML and absence of unresolved placeholders.
- [ ] Visually inspect the live DOCX outputs on the Mac.

Target templates were inspected in place, never replaced by legacy copies or edited. Noc_Template.docx has the association_name-only title. Affidavit_Template.docx has separate LAND and adjacent PROJECT_LOCATION placeholders. Consent_Template.docx has fixed indices 0–4 and society_name/society_address in its Word header. No template mismatch blocked this implementation.

## Files and responsibilities

| Files | Responsibility |
| --- | --- |
| `models.py` | Field/spec/config/result contracts and safe diagnostic exception types |
| `config_manager.py` | Unique-key safe YAML parsing, single-file path/schema/pattern validation |
| `document_registry.py`, `documents/__init__.py` | Explicit registry and adapter package |
| `documents/noc.py`, `documents/affidavit.py`, `documents/consent.py` | Versioned exact headings, explicit aliases, requiredness and context assembly |
| `document_generator.py` | Heading normalization, validation, date transport, XML inspection, strict rendering, filename sanitization and atomic save |
| `sheets_service.py` | Exact service-account worksheet access, formatted strings, physical row snapshots and RAW operational writes |
| `processor.py` | Shared preflight, eligibility, row change detection, save/sync outcomes and progress callbacks |
| `main.py` | CLI parsing, safe diagnostics and exit codes |
| `tests/` | Offline fixtures, actual-template render checks, fake Sheets, failure injection, config/CLI and standalone checks |
| `requirements.txt`, `.gitignore` | Tested direct dependency pins and exclusions |
| `config.yaml` | Ignored placeholder runtime config, created only because absent |
| `README.md`, `IMPLEMENTATION_NOTES.md` | Setup, Mac test handoff, decisions and verification evidence |

The supplied plan/specification and DOCX templates were not edited by the implementation. Existing working-tree changes to supplied files were left alone. No parent Git configuration, sibling source/environment, Windows package or installer was changed. No nested repository was initialized and no commits were made.

## Reused logic and intentional changes

- NOC: adapted NFC/BOM/whitespace/slash/case heading normalization, the reviewed address alias, status eligibility, basename reporting and processed-at/error semantics. The new primary address label comes from the latest Form contract. Added required-value validation (12 fields), explicit date transport instead of guessing, strict preflight, string-preserving ingestion, grouped RAW writes, row snapshots and local-save/status-sync distinction. Optional Signatory Role stays blank. Association-name text is never rewritten.
- Affidavit: adapted the uppercase context mapping, integer age range 1–120, required-value/XML validation, autoescaping and unresolved-placeholder checks. Added the seventeenth input PROJECT_LOCATION and explicit transport from Sheet date strings. LAND is Khasra numbers only. No alias for historical combined land/location answers is assumed valid. Curly and straight Father's Name apostrophes are explicit reviewed aliases with tests.
- Consent: adapted its five-member dictionary structure and Unicode-safe filename principle. Latest Form requiredness overrides the old six-field validator: 23 required, only Document Date optional. No old place/designation defaults or applicant-to-signatory copying. Strict undefined rendering replaces the old permissive render path.
- Configuration: replaced legacy AppData/fallback rules with one active YAML file, defaulted beside main.py, with all paths resolved relative to that file. Credentials stay separate. There is no `.env`, additional active settings file or hidden legacy import.

There are no fuzzy aliases or invented document fields. Every Form column, including optional-answer columns, is mandatory in the Sheet schema. The 24 Consent leaf fields produce 14 scalar render keys and one five-entry members container.

## Environment and dependency evidence

Interpreter: `/Users/mac/python/jobmitra/legal-document-generator/.venv/bin/python`

Python: `3.11.0`, macOS arm64, Clang 13.0.0. Environment created with the already available `/usr/local/bin/python3`; no Python upgrade or sibling environment reuse.

Setup command from the parent workspace:

```bash
legal-document-generator/.venv/bin/python -m pip install -r legal-document-generator/requirements.txt
```

The first sandboxed install failed to reach the package index. Installation was retried through the approved network escalation and completed in the project environment. Tested direct versions: gspread 6.2.1, google-auth 2.58.0, docxtpl 0.20.2, python-docx 1.2.0, Jinja2 3.1.6, PyYAML 6.0.3, pytest 9.1.1. These are pinned in requirements.txt; it is not a freeze of another environment.

## Verification results

Commands run from the target project with its explicit interpreter:

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/python -m pip check
.venv/bin/python main.py list-documents
.venv/bin/python main.py validate-config
```

Latest offline suite: **143 passed**. No failed or skipped tests in that run. All 51 required fields are tested individually with whitespace-only values. Coverage includes all current mappings, optional dates/role, real-template text/style/header checks, NOC city preservation, Affidavit split location, all Consent members, explicit ambiguous-date conventions, identifiers, special XML text, missing/duplicate headings, schema failures, selected physical rows, status skips/retries, changed snapshots, failures before claims, render/save failures, uncertain claim/success/error writes, clean dry runs and isolated output directories. A standalone temporary copy rendered all three templates without the legacy projects. Test sockets are disabled in-process; standalone subprocess checks execute local preflight only.

`pip check`: no broken requirements. `list-documents`: reports the expected 14/17/24 schemas. Initial `validate-config` correctly rejected the unresolved spreadsheet-ID placeholder. After the user provisioned credentials and the spreadsheet ID, active `validate-config` passed for all three templates; credential-file presence is confirmed. Authentication also succeeded during subsequent read-only Sheet checks.

The user subsequently added the project's credentials.json and spreadsheet ID. Secret contents were never displayed, logged or copied; only the Google authentication library read the configured credential file during authorized read-only access. Git checks confirm config.yaml and credentials.json are ignored and untracked.

Live read-only checks succeeded for all three exact worksheets. Initially, all four nonblank certificate dates failed the ISO example setting and matched only `%m/%d/%Y` among supported formats. The three local YAML input_date_format values were changed to `%m/%d/%Y` based on that unambiguous evidence; the user's spreadsheet ID, credential reference and other settings were preserved. Nothing in the live spreadsheet was reformatted or edited. Subsequent checks had zero date mismatches. All current Document Date values were blank, so nonblank Document Date transport remains to be exercised by a later test submission.

Observed selected pilot scope: NOC Responses row 3, Affidavit Responses row 2, Consent Responses row 2. NOC also has one pre-existing row with an ineligible status, which was not selected. Each selected-row live dry-run passed with `would_generate=1`, zero invalid rows and no Sheet writes or persistent DOCX outputs. The user subsequently explicitly instructed running the three exact generation commands. They ran sequentially: NOC row 3, Affidavit row 2, and Consent row 2 each returned generated=1, zero failures and zero synchronization errors, with exit code 0. Each file exists, its ZIP/XML is valid, and no unresolved double-brace placeholders remain.

The approved generation saved three live DOCX files and reported successful operational-cell updates for the three selected rows. No Form or worksheet schema changes were made. No additional rows were selected. Public API documentation and package downloads were also accessed. No GUI visual layout inspection is claimed. No Windows work was undertaken.

## Operational limits and next actions

The row/status re-read is not a distributed lock. Only one worker should process a worksheet; keep rows append-only during a run. File save and Sheet synchronization are not transactional. A file can exist after a failed status update, and an uncertain claim can leave PROCESSING. A deterministic retry can overwrite the same local filename; changed filenames or moved rows can produce another file. Never automatically reset PROCESSING or force a GENERATED row.

Configuration and read-only checks are complete. The identified rows have now been explicitly approved and generated. Follow the visual acceptance and subsequent skip/retry checks in README; those further checks have not been run automatically. Perform visual Word review and the skip/retry/output-folder acceptance checks there. Configuration/credentials are not included in tracked distribution and must be provisioned when copying the application.

Phase 2 is deliberately deferred: dynamically generated Tkinter tabs, Windows execution environment, packaging and installer decisions will reuse this backend and be tested separately. This implementation makes no Windows or production readiness claim.

## User-requested Affidavit age formatting correction

After live generation, the user reported that age 20 was larger than the surrounding text. The AGE run in the target Affidavit template had explicit `w:sz` and `w:szCs` values of 32 (16 points), while the normal document size is 24 (12 points). Removed only those two size overrides so the age inherits the normal size. Other formatting, text and ZIP parts were preserved; no backend font-size transformation was added.

The previous local output was no longer present when applying the correction. Affidavit row 2 was read again and regenerated locally from the corrected template without changing Sheet cells or resetting GENERATED. The age run in the new output has no explicit size override. macOS Quick Look preview of the age line was visually inspected and shows 20 at the normal text size. This targeted preview is not a full Word pagination certification; the bundled LibreOffice renderer is unavailable on this Mac. Legacy templates/projects were not modified.

## Phase 2 desktop implementation — 23 September 2026

This section supersedes the earlier Phase-2 deferral. The historical Phase-1
verification notes above remain a record of those earlier runs.

The initial regression run found 162 passed / 1 failed. The Affidavit style test
compared XML bytes, while python-docx normalized declaration quotes and a newline
in styles.xml and numbering.xml. Canonical XML was identical, and a plain
python-docx open/save reproduced the difference without the application renderer.
The approved test correction applies canonical comparison to XML styling resources
for every adapter, retaining exact binary-asset comparisons. The corrected baseline
passed all 163 tests before desktop implementation began. No template changed.

### Implementation

- `app.py`: source/windowed entry point, contained startup errors and rotating
  application logging. Startup loads local configuration; no Sheets calls.
- `desktop.py`: one `DocumentTab`, registry-generated Notebook pages, main-thread
  controller, background call to the existing `processor.run_batch`, queue polling,
  one-job guard, independent result feedback, native folder selection and platform
  folder opening. A live job prevents closure until it finishes.
- `desktop_config.py`: the existing strict loader plus atomic, validated YAML
  persistence for the selected output directory. Reads fresh settings before
  writing; a failed validation or replace preserves the previous file. YAML
  comments/formatting are normalized on save; unrelated setting values remain.
- `runtime_paths.py`: per-user Windows AppData identity, redirected Documents
  defaults and PyInstaller resource lookup. Source CLI path behavior is unchanged.
  Packaged relative templates resolve in the bundle, while credentials and output
  paths retain their config-relative semantics. Bundle paths are never persisted.
- Packaging: `legal_document_generator.spec`, `requirements-build.txt`,
  `build_windows.bat`, `install_windows.ps1`, `config.example.yaml` and
  `WINDOWS_DEPLOYMENT.md`. The example YAML is only an installer seed. It is not
  loaded as fallback runtime settings, and is not bundled into the EXE.
- Verification: `tests/test_desktop.py`, `tests/test_desktop_runtime.py`, and the
  display-required `scripts/smoke_gui.py`. Existing Phase-1 tests are preserved.

The desktop does not contain business mappings or per-document processors. Registry
and config additions plus a reviewed adapter/template are sufficient for future
tabs. Generate runs the entire eligible batch of the selected document; selected-row
operations remain available through the existing CLI. Failed UI counts aggregate
failed, invalid, changed and sync_failed outcomes; synchronization warnings remain
explicit. Worker threads enqueue results and never access Tk widgets or `after`.

Logs record document key, destination, start/end summaries, backend row diagnostics
and sync failures. Unexpected errors record types, causal types and stack locations,
not potentially secret cloud exception payloads. Explicit Phase-1 SetupError
messages are logged separately. Credentials are never opened by the GUI itself.

### Final verification

- Complete offline suite: **213 passed**, no failed/skipped tests (17.35 seconds).
  This includes 163 baseline tests and 50 desktop/runtime tests. Network connections
  remain blocked by the existing fixture; GUI-to-backend integration uses fake Sheets.
- Real macOS Tk 8.6 smoke test: **passed**, twice, including after runtime-path
  support. A real window displayed and switched through all three tabs. A fake
  Affidavit job disabled every Generate button, completed through queue polling,
  updated only Affidavit results, restored controls and closed normally.
- `.venv/bin/python main.py list-documents`: passed, all three schemas reported.
- `.venv/bin/python -m pip check`: no broken requirements.
- `git diff --check`: passed.
- No live Sheets generation or network Sheet checks were used. No credentials,
  real config, generated output, document templates, adapters or Phase-1 production
  modules were modified. No legacy sibling project was modified.
- No Windows EXE was built on macOS. The spec was executed with offline PyInstaller
  doubles to verify explicit template inclusion, secret exclusion by project asset
  allowlist, output name and no-console configuration. This does not replace a real
  Windows build or binary-content inspection.

### Final project structure

```text
legal-document-generator/
├── app.py                         # desktop entry point (added)
├── desktop.py                     # reusable view/controller (added)
├── desktop_config.py              # shared YAML persistence (added)
├── runtime_paths.py               # source/packaged locations (added)
├── main.py                        # existing CLI, unchanged
├── config_manager.py              # existing strict loader, unchanged
├── document_registry.py           # existing registry, unchanged
├── processor.py                   # existing shared processor, unchanged
├── sheets_service.py              # existing Sheets client, unchanged
├── document_generator.py          # existing renderer/validation, unchanged
├── models.py                      # existing contracts, unchanged
├── documents/                     # existing three adapters, unchanged
├── templates/                     # existing three DOCX files, unchanged
├── tests/
│   ├── test_desktop.py             # added
│   ├── test_desktop_runtime.py     # added
│   ├── test_documents.py           # XML-comparison correction only
│   ├── test_config_cli.py          # unchanged
│   ├── test_processor.py           # unchanged
│   ├── conftest.py, helpers.py     # unchanged
│   └── fixtures/                  # unchanged
├── scripts/smoke_gui.py            # added, offline real-window smoke test
├── config.example.yaml            # added, redacted installer seed
├── config.yaml                    # ignored active source settings, unchanged
├── credentials.json               # ignored secret, unchanged
├── requirements.txt               # existing runtime/test pins, unchanged
├── requirements-build.txt         # added, Windows build pins
├── legal_document_generator.spec  # added
├── build_windows.bat              # added
├── install_windows.ps1            # added
├── WINDOWS_DEPLOYMENT.md           # added
├── README.md                      # updated desktop entry points
├── IMPLEMENTATION_NOTES.md        # this Phase-2 record appended
├── FORM_SPEC.md                    # unchanged
├── CODEX_PHASE1_IMPLEMENTATION_PLAN.md # unchanged
└── .gitignore                     # allow reviewed build spec
```

The existing local `.venv`, caches, logs and generated directories remain ignored.
No commit was created by this implementation.

### Handoff and remaining Windows acceptance

Source launch: `.venv/bin/python app.py`.

Windows build after environment setup: `.\build_windows.bat`.

Windows install from project/release layout:
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1`.

The real Windows build, dependency hooks/Tcl bundling, executable launch, shortcut
creation, installer execution and upgrade preservation still require a Windows
machine. Also verify redirected Documents, Unicode/network output paths, AppData
permissions, office Microsoft Word layout/fonts, and explicitly approved live
Sheets access/generation/sync failure handling. The deployment guide contains the
full setup and acceptance procedure. The app prevents overlapping jobs within one
window, not across machines or multiple application instances.

## Windows test portability correction

A Windows run reported 117 failures / 96 passes, with repeated CP1252 decoding
errors loading the Hindi JSON fixtures and FORM_SPEC.md. Reproduced the exact
fixture error locally by decoding the UTF-8 bytes as CP1252 (undefined byte 0x8d
at offset 39). Test fixture/spec reads now explicitly select UTF-8; the remaining
test text-file reads/writes also specify UTF-8 to remain independent of the locale.
Production configuration I/O already selected UTF-8 and was not changed.

Also replaced slash-based template basename extraction in the standalone-copy test
with Path.name, which supports native Windows backslash paths. The Windows build
version guard now prints the interpreter/version and exits explicitly for anything
other than Python 3.11 or 3.14, rather than relying on an assertion that Python
optimization can disable. The user confirmed that Python 3.14 is intentional on
Windows, so the build guard and deployment guide now accept that target. PyInstaller
6.22.3 includes 3.14 support. This is separate from the encoding defect; full
Windows/Python 3.14 application and executable verification remains pending.

Added five regression cases simulating CP1252 defaults for all three Hindi fixtures,
the Form contract checks and a Hindi output-directory YAML round trip. Verification:
**218 offline tests passed locally on macOS in 18.16 seconds**. Windows rerun/build
is still required; no Windows execution or EXE build is claimed for this correction.
