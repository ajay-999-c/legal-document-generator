# Codex implementation task — Phase 1: Mac backend and CLI

## Objective and working directory

Implement a standalone, reusable Google Forms → Google Sheets → DOCX backend for NOC, Affidavit, and Consent Letter inside `jobmitra/legal-document-generator/`.

Start this Codex session from the parent workspace, `jobmitra/`, so the three existing projects can be inspected. Treat the existing `noc/`, `affidavit/`, and `consern/` applications as reference material, not as folders to refactor or runtime dependencies.

**Source/configuration/documentation write scope: `legal-document-generator/` only.** Isolated temporary test directories are permitted; live document output is permitted only when the user runs or approves generation into the configured destination. Do not modify parent files, sibling applications, their configuration, their environments, or their generated documents. Respect applicable `AGENTS.md` instructions. Do not rename `consern/`.

Implement this phase, rather than returning only another plan. First inspect, record a brief implementation checklist, then make incremental changes and run offline tests. Finish by handing over explicit commands for the user’s real Mac/Form tests.

**Do not implement Tkinter, Windows packaging, an installer, Streamlit, or a new web interface in this phase.** The next phase will add one Windows application with browser-like document tabs using this same backend.

## 1. Read and verify before editing

Read these inputs from the workspace root:

- `dir_tree.md`.
- `legal-document-generator/FORM_SPEC.md`: this must be the latest regenerated specification reflecting 23 September 2026 Form requiredness.
- `noc/REPLICATION_GUIDE.md` and the relevant existing source/tests.
- `noc/config_manager.py`, `sheets_service.py`, `document_generator.py`, `processor.py`, `generate_from_sheet.py`, and the reusable behavior in `app.py`.
- `affidavit/src/`, its application entry point, README, and tests.
- `consern/AGENTS.md`, `app.py`, `document_generator.py`, README, and available tests.
- The three actual DOCX files already placed in `legal-document-generator/templates/`.

The reported filenames are:

```text
templates/Noc_Template.docx
templates/Affidavit_Template.docx
templates/Consent_Template.docx
```

List that directory and use its exact filenames and capitalization. Do not assume the older lowercase NOC filename is still the target. Do not overwrite the user's new templates with legacy copies.

The current target contracts override conflicting older application behavior:

| Key | Worksheet | Input fields | Required | Optional |
| --- | --- | ---: | ---: | --- |
| `noc` | `NOC Responses` | 14 | 12 | `document_date`, `signatory_role` |
| `affidavit` | `Affidavit Responses` | 17 | 16 | `document_date` |
| `consent` | `Consent Responses` | 24 | 23 | `document_date` |

Requiredness comes from the latest Form specification, not the old Consent validator that required only six fields. No “needs business confirmation” field should remain for these required/optional decisions.

If the current `FORM_SPEC.md` is the old 16-field Affidavit / 6-required Consent version, stop and report that the latest `FORM_SPEC_REGENERATED.md` must be installed as `FORM_SPEC.md`. Do not silently implement an outdated contract.

All actual DOCX placeholders use double braces. An isolated prose typo such as `{association_name}` in the regenerated spec does not change the actual `{{association_name}}` contract. Preserve placeholder case, especially the uppercase Affidavit keys.

Inspect template placeholders across paragraphs, tables, headers, and footers. Account for Word text split across runs. Do not make template wording, formatting, legal-text, or layout edits automatically. Report a mismatched template and continue only the unaffected development/testing work; do not claim the affected document is ready.

## 2. Separate environment and dependencies

Use only `legal-document-generator/.venv/` for this new project. Do not reuse, copy, clear, or install into a parent or sibling `.venv`, the Conda base environment, or system packages.

If the user has already created the target environment, inspect its Python executable/version and reuse it if suitable. Otherwise create it using an available compatible Python interpreter. Check the installed version first; favor the existing supported interpreter instead of upgrading Python or installing a different interpreter without approval.

From `jobmitra/`, the intended commands are:

```bash
python3 -m venv legal-document-generator/.venv
legal-document-generator/.venv/bin/python -c "import sys; print(sys.executable); print(sys.version)"
```

Run these only after checking whether the environment already exists. For every subsequent command use the explicit target interpreter; do not rely on the shell's `(.venv)` label or `python` resolving to the right project.

Create **one `requirements.txt`** in the target project. Keep dependencies small: `gspread`, `google-auth`, `docxtpl`, `python-docx`, `Jinja2`, `PyYAML`, and `pytest` as needed. Inspect the legacy requirements, select compatible versions, test them in the new environment, and record the tested versions. Do not blindly freeze the user's old environment. Do not add pandas, a server framework, Streamlit, an LLM framework, PyInstaller, or a pip package named tkinter.

Missing network/package-install permission is a reported setup blocker, not a reason to bypass sandbox restrictions or claim tests passed.

## 3. Standalone structure with shared components

Use the existing small-module approach. A suitable target structure is:

```text
legal-document-generator/
├── .venv/                         # local, ignored
├── FORM_SPEC.md
├── CODEX_PHASE1_IMPLEMENTATION_PLAN.md
├── main.py                        # thin CLI entry point
├── config.yaml                    # only active runtime settings file; ignored
├── requirements.txt
├── .gitignore
├── README.md
├── IMPLEMENTATION_NOTES.md
├── config_manager.py
├── document_registry.py
├── sheets_service.py
├── document_generator.py
├── processor.py
├── models.py                      # small shared data/result types if useful
├── documents/
│   ├── __init__.py
│   ├── noc.py
│   ├── affidavit.py
│   └── consent.py
├── templates/
│   ├── Noc_Template.docx
│   ├── Affidavit_Template.docx
│   └── Consent_Template.docx
├── tests/
│   ├── fixtures/                  # synthetic inputs; no client data
│   └── test_*.py
├── generated/                     # configurable defaults; ignored
│   ├── noc/
│   ├── affidavit/
│   └── consent/
└── logs/                          # ignored
```

Keep the module count modest. Small shared dataclasses can live in `models.py`; do not create an unnecessary enterprise/plugin framework.

Reuse suitable logic by adapting it into this project once. Never use `sys.path` hacks, runtime imports from sibling applications, or a dependency on a sibling virtual environment. The new project must work when copied without the old three projects.

Responsibilities:

- `config_manager.py`: load and validate the one YAML file; resolve paths; expose typed settings.
- `document_registry.py`: join enabled document settings with known, explicitly registered document adapters.
- `documents/*.py`: versioned field mappings, reviewed aliases, required fields, and document-specific context assembly.
- `sheets_service.py`: authenticate, open the exact spreadsheet/worksheet, preserve row addresses, read values, and update operational cells.
- `document_generator.py`: shared trimming, safe date conversion, filename sanitization, template checks, strict rendering, and file save helpers.
- `processor.py`: one common per-document processing workflow, status handling, and structured results.
- `main.py`: argument parsing and CLI output only; no duplicated business logic.

Do not put NOC/Affidavit/Consent branches throughout the shared processor. Use a DocumentSpec/adapter contract. Adding a later document should need its schema/adapter, template, and YAML entry—not a new processor or CLI generation function.

## 4. One runtime configuration file

All administrator-editable runtime settings must be in `legal-document-generator/config.yaml`: spreadsheet ID, credential-file path, worksheet names, template paths, output directories, filename patterns, enabled document types, date transport formats, and logging settings.

Do not introduce `.env`, `settings.json`, per-document YAML files, AppData settings, environment-specific YAML files, or a second active configuration source in Phase 1. Document a redacted YAML example in README rather than creating competing config files.

**Credential exception:** a Google service-account JSON is a secret, not a second settings file. Keep it as a separately secured, untracked file and reference its path in YAML. Never paste a private key into YAML, source, tests, logs, or the task response. Do not display or copy old credential contents. The user will provision the credential file; runtime use through the authentication library is permitted when the user runs a live command.

Create a placeholder `config.yaml` only if absent. Do not overwrite a populated configuration. The existing service account can be used if it has the necessary spreadsheet access; do not create a new account or key as part of coding.

Suggested configuration contract, subject only to small documented implementation adjustments:

```yaml
schema_version: 1

app:
  name: "Legal Document Generator"
  log_file: "logs/generator.log"
  log_level: "INFO"

google:
  spreadsheet_id: "YOUR_SPREADSHEET_ID"
  credentials_file: "credentials.json"
  scopes:
    - "https://www.googleapis.com/auth/spreadsheets"

formatting:
  document_date_format: "%d-%m-%Y"
  processed_at_format: "%d-%m-%Y %H:%M:%S"
  blank_document_date: ".........."

processing:
  error_message_max_length: 500

documents:
  noc:
    enabled: true
    label: "NOC"
    worksheet_name: "NOC Responses"
    template_path: "templates/Noc_Template.docx"
    output_dir: "generated/noc"
    filename_pattern: "NOC_{project_name}_{recipient_name}_{row_number}.docx"
    input_date_format: "%Y-%m-%d"

  affidavit:
    enabled: true
    label: "Affidavit"
    worksheet_name: "Affidavit Responses"
    template_path: "templates/Affidavit_Template.docx"
    output_dir: "generated/affidavit"
    filename_pattern: "AFFIDAVIT_{name}_{row_number}.docx"
    input_date_format: "%Y-%m-%d"

  consent:
    enabled: true
    label: "Consent"
    worksheet_name: "Consent Responses"
    template_path: "templates/Consent_Template.docx"
    output_dir: "generated/consent"
    filename_pattern: "CONSENT_{project_name}_{applicant_name}_{row_number}.docx"
    input_date_format: "%Y-%m-%d"
```

The example ISO input-date formats are **not a claim about the live Sheets**. Check actual returned date strings before generation. Configure the matching representation, such as `%m/%d/%Y`, explicitly when needed. Do not guess ambiguous slash dates or silently change a live Sheet's formatting.

Field maps and validators are versioned document business rules in `documents/*.py`, not a second administrator-settings store. Fixed status names and exact operational-column names remain the agreed data contract, not free-form customization.

Default config discovery must use the location of `main.py`, not the shell's working directory. Support `--config PATH`. Resolve every relative path inside YAML against that YAML file's resolved parent directory; expand `~` and support absolute paths. Each output directory is the final destination—do not append an extra document subfolder to an explicitly chosen folder.

Use safe YAML loading and clear schema errors. Reject duplicate configuration keys, unsupported enabled document keys, invalid/missing settings, unresolved spreadsheet-ID placeholders, full spreadsheet URLs or IDs with trailing slashes, and invalid filename patterns. Do not fall back to a random worksheet or silently guess a template filename.

Validation/generation of one selected type should not be blocked by a missing template for an unrelated type; `validate-config` can report all types individually.

Add a project-local `.gitignore` covering `.venv/`, `__pycache__/`, `.pytest_cache/`, `config.yaml`, `credentials.json`, `secrets/`, generated outputs, preview outputs, logs, and later build artifacts. Do not blanket-ignore all JSON because synthetic test fixtures may use JSON. Do not modify parent Git configuration, initialize nested repositories, commit, reset, clean, or push automatically.

## 5. Exact document contracts

### NOC

Use all 14 mappings from the latest specification. Required fields are all except `document_date` and `signatory_role`.

The current association address heading is:

```text
Association Location / Address / एसोसिएशन का स्थान / पता
```

Preserve this reviewed legacy alias:

```text
Association Address / एसोसिएशन का  पता
```

Both map to `association_location`. Two columns resolving to that same field are an ambiguity error, not a reason to choose one silently.

`association_name` is the submitted text with surrounding whitespace trimmed. The title uses `{{association_name}}`; the template and backend must not append, remove, or rewrite any city suffix. `association_location` remains a separate field.

Optional `signatory_role` becomes an empty string, not a fabricated designation.

### Affidavit

Use all **17** mappings. Every field except `document_date` is required.

Keep these inputs separate:

```text
Khasra Number(s) / खसरा नंबर
→ land_details
→ {{LAND}}

Project Location / परियोजना का स्थान
→ project_location
→ {{PROJECT_LOCATION}}
```

Do not parse the address out of `LAND`, combine the values into one field again, or duplicate the location. Historical responses lacking the new location require correction; do not fabricate one. A old label alias, if retained and documented, does not make old combined data automatically valid.

Translate snake_case parameters into the existing uppercase render keys, including `PROJECT_LOCATION`. Preserve the established integer age validation after checking the old validator; the prior audit describes 1–120 inclusive. Do not cast plot/certificate/Khasra identifiers to numbers. Plot help text requesting a number is not evidence for a new arithmetic/numeric-only backend restriction.

### Consent Letter

Use key `consent`, not `concern` or `consern`. Keep the legacy source folder untouched.

Use all **24** mappings. All 23 fields other than `document_date` are required, including both addresses, project location, certificate number/date, plot number, place, all five member names and designations, and signatory name.

Assemble exactly five dictionaries in the existing fixed order:

```python
members = [
    {"name": values["member_name_1"], "designation": values["member_designation_1"]},
    {"name": values["member_name_2"], "designation": values["member_designation_2"]},
    {"name": values["member_name_3"], "designation": values["member_designation_3"]},
    {"name": values["member_name_4"], "designation": values["member_designation_4"]},
    {"name": values["member_name_5"], "designation": values["member_designation_5"]},
]
```

The 24 input/leaf mappings are not 24 top-level render keys; `members` is one container. Validate every indexed name/designation, not merely the existence of `members`.

Do not fill blank names/designations/place using old Streamlit defaults. Do not copy applicant name into signatory name automatically. Verify society name/address rendering in the Word header as well as the body/table.

## 6. Shared mapping, validation, and rendering

Normalize **headings** using the established Unicode NFC, BOM removal, case-folding, repeated/edge whitespace and line-break handling, and slash-spacing handling. Use explicit reviewed wording aliases; no fuzzy matching. Curly versus straight apostrophes need an explicitly supported treatment/alias and a test, not accidental matching.

Require every specified document header, including optional-answer columns. Missing header is a setup/schema error; a blank optional value is permitted. Reject duplicate/ambiguous mapped headers. Do not silently ignore a missing required field by using `.get(..., '')` all the way to generation.

Trim values only as specified. Preserve meaningful internal newlines, Hindi text, spelling, and city names. Validate nonblank required values after trimming. Keep identifier values such as `026`, `343/1`, and certificate/RERA numbers as text throughout ingestion, context creation, and output.

A Date question's visible `dd-mm-yyyy` input is not proof of the format returned by Sheets. Use the configured input format, reject invalid/unknown dates with an actionable row error, and render valid dates in `DD-MM-YYYY`. Do not use month-first/day-first guess loops. Every completion-certificate date is now required. Every omitted Document Date becomes exactly ten dots, never today.

Render with a fresh `DocxTemplate` for each row, Jinja `StrictUndefined`, and appropriate XML autoescaping. Test `&`, `<`, and `>` in valid text without corrupting Word XML. Check unexpected template variables and required placeholder coverage before live status changes; verify nested Consent member paths with context tests and a strict synthetic render rather than assuming top-level variable discovery validates them.

Preserve template wording, paragraph/run formatting, tables, headers, and footers. Do not rebuild the DOCX from extracted plain text.

Sanitize filename components cross-platform while retaining usable Hindi text. Prevent path traversal/control characters and unreasonable filename lengths. Keep `.docx` as the extension. Use a temporary file in the output directory and replace the final target only after successful save. Retrying the same logical row may replace its deterministic existing filename, matching the prior retry behavior; document this overwrite behavior clearly.

The pilot uses sheet row numbers in filenames under an append-only workflow. Row numbers are not permanent candidate/document IDs: do not sort, insert, delete, or move rows while a batch is running. Do not claim exactly-once generation across row moves, changed filenames, multiple machines, or a lost status update.

## 7. Google Sheets service and common processor

Connect through the configured existing service account and `open_by_key`-style access to the exact spreadsheet. Reading the selected worksheet and updating its operational cells is the only required cloud operation. No Form creation, worksheet creation, auto-renaming, schema edits, new API project, or document upload in this phase.

Read values without automatic numeric conversion of identifiers. If using `get_all_records`, explicitly disable numericisation appropriately; alternatively map raw value rows after validating headers. Preserve physical sheet row numbers even when there are empty rows. Pad trailing empty cells rather than shifting fields. Skip genuinely empty non-submission rows without losing indexing.

Map operational columns by their exact header names, never hardcoded positions such as P:S:

```text
processing_status
generated_file
processed_at
error_message
```

Only these operational cells may be written. Submitted data and `Timestamp` must not be edited.

Normalize status with trim plus uppercase:

| Status | Behavior |
| --- | --- |
| blank | Process |
| ERROR | Retry once during this invocation |
| PROCESSING | Skip |
| GENERATED | Skip |
| any other nonempty value | Skip |

Do not add an infinite retry loop or a force option that reprocesses GENERATED rows. Selecting a row explicitly does not override its status eligibility.

Before processing, complete selected-document preflight: valid configuration, template/schema/context compatibility, destination access, worksheet access, and unambiguous headers. A missing template must not turn every row into ERROR.

For each eligible selected row:

1. Preserve its physical row number and submitted-value snapshot.
2. Confirm its identity/status has not changed before mutation. Treat this as a change-detection safeguard, not an atomic claim/lock.
3. Write PROCESSING and clear the old error message.
4. Validate/map/render/save the selected document using the shared components.
5. After a successful save, update the four operational fields together using one values batch update with literal/RAW input: GENERATED, filename, processing timestamp, and empty error.
6. On validation/render/save failure, attempt ERROR plus a concise field-oriented error truncated to the configured limit; continue to the next eligible row.
7. If the local file was saved but Sheets status synchronization fails, report that distinction and the local output path. Do not count the row as fully successful or claim no file exists. If recording ERROR also fails, report it separately.

A grouped Sheet write is not a transaction with the local filesystem and not a distributed lock. Phase 1 runs one selected document batch sequentially. Document that only one process/machine/legacy app should process a given worksheet at a time. Never automatically reset stale PROCESSING rows: the operator must inspect the output first.

Use sensible API timeouts and bounded retry behavior for transient transport failures; do not repeatedly regenerate files in an unbounded loop. Avoid full client records, credentials, access tokens, and private-key material in CLI output or logs.

Return a structured BatchResult with document key, counts, row outcomes, saved paths, and synchronization errors. Provide an optional plain-Python progress callback/event interface so Phase 2 can reuse the same workflow without importing Tkinter into the backend.

## 8. CLI contract and safe testing modes

Implement the following command interface, from inside `legal-document-generator/`:

```bash
python main.py list-documents
python main.py validate-config
python main.py check-sheets --document noc
python main.py check-sheets --document affidavit
python main.py check-sheets --document consent
python main.py generate --document noc --rows 2 --dry-run
python main.py generate --document noc --rows 2
python main.py generate --document affidavit --rows 2
python main.py generate --document consent --rows 2
```

Row 2 is an example only. The operator must substitute the actual physical row number of the designated test submission in each worksheet. Support comma-separated physical row numbers, reject header row 1 and invalid numbers, and allow omission of `--rows` for a later full eligible batch of the selected document only.

Do not implement `generate-all`, automatic generation on startup, polling, background scheduling, or parallel document-type jobs.

Command semantics:

- `list-documents`: local registry summary only; no Google connection.
- `validate-config`: local schema/path/template checks with per-document diagnostics; do not mutate Sheets. Report missing credentials separately from template validation; never expose credential contents.
- `check-sheets`: read-only access and heading diagnostics for the selected worksheet; show counts and date-transport diagnostics without dumping personal values. Do not claim Editor/write permission is proven by a read-only call.
- `generate --dry-run`: fetch/validate selected rows and render only to an automatically cleaned temporary location for validation. Do not modify Sheet cells, create persistent DOCX outputs, or overwrite generated files. Report would-generate/skipped/invalid, not actual GENERATED results.
- `generate` without dry-run: explicitly writes selected eligible rows' statuses and their local DOCX files. Print a concise final result and meaningful exit code.

Tests and imports must never contact Google. Do not run a live mutating generation command during unattended implementation unless the user has separately supplied and approved the exact test worksheet/row scope. Offline development must still finish when credentials or network are unavailable.

## 9. Offline tests and acceptance gates

Use fake Sheets and temporary directories. Generate DOCX files using the actual new target templates and synthetic, clearly fictitious Hindi/English inputs.

Required test coverage:

1. Exact field counts, required/optional lists, and per-document mappings from the latest spec.
2. One full valid render per template; inspect expected text in body, table, header/footer as applicable. File existence alone is insufficient.
3. Parameterized rejection of every required field when blank/whitespace-only, including all ten Consent member fields.
4. Optional Document Date → ten dots for all types; blank optional NOC signatory role → empty string.
5. Affidavit separate LAND and PROJECT_LOCATION rendered once in the intended adjacent location; uppercase mapping preserved.
6. NOC with and without a city suffix preserves submitted association_name; no fixed Indore insertion/removal.
7. Consent fixed member order and all names/designations; header-only society-address coverage.
8. Configured date parsing, invalid dates, ISO values, explicit month-first/day-first configurations, and an ambiguous slash date that is never guessed.
9. Numeric-looking identifier preservation and valid special XML characters.
10. Heading spaces, newlines, BOM, slash spacing, reviewed aliases; missing and duplicate/ambiguous headers, including an absent optional-value header.
11. Blank/ERROR eligibility with mixed case/spaces; PROCESSING/GENERATED/unknown statuses skipped; a second run does not regenerate successful rows.
12. Preflight failures before status mutation; row validation/render/save failures; failure to write success/error status; local-file-saved versus status-synchronized distinction.
13. Physical row indices preserved across blank rows, selected-row scoping, and detection of changed row data/status before writes.
14. Dry-run performs zero Sheet mutations and leaves no persistent generated DOCX.
15. Running from a different working directory; config-relative/absolute output paths with spaces; independent per-document directories.
16. Wrong worksheet must not fall back to another one; no cross-document output/status changes.
17. Standalone imports without sibling applications; no network or real credentials in automated tests.

Use the explicit project interpreter, with the target project as the test working directory:

```bash
(
  cd legal-document-generator
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/python -m pytest tests -q
)
```

Do not report a test as passed unless run. Record failed/skipped/not-run checks separately.

## 10. Incremental implementation order

Work in these gates, keeping the existing applications untouched:

1. **Inventory and setup:** inspect sources/new templates, check newest spec, create/reuse the isolated environment, dependencies, and local ignore rules.
2. **Config and registry:** single YAML loader/path semantics and three document specs; no cloud connection on import.
3. **Offline generation:** common validators/rendering plus three context builders, tested against real templates with synthetic inputs.
4. **Sheets and processor:** common row reading/status handling, safe CLI, selected-row and dry-run support with fake-Sheets tests.
5. **Mac test handoff:** final offline suite, README commands, configuration guide, designated live Form tests, and candid status report.

Update `IMPLEMENTATION_NOTES.md` with the actual source logic reused, intentional differences from the legacy validators, blockers, tests run, and commands still requiring user execution. Do not mark the project live-verified just because mocks passed.

## 11. Real Mac/Form acceptance procedure to document

The user will fill the three existing Google Forms. No new Forms are to be created.

1. Provision the existing credential file securely and fill the spreadsheet ID in the new YAML. Confirm configured worksheet names exactly match the existing workbook.
2. Use read-only `check-sheets` for each type; confirm mappings and the configured input-date format match the actual delivered data. Do not move historical data or reset statuses.
3. Submit one clearly marked TEST response in each Form. Record the actual row number in each worksheet. It need not be 2, and the three rows need not have the same number.
4. First run a selected-row dry-run for each document.
5. Run generation for only those three designated test rows, one document type at a time.
6. Confirm three files appear in the three configured directories and that only the corresponding worksheet rows' operational cells changed.
7. Open the DOCX outputs on the Mac and inspect Hindi text, every supplied value, dates, project location, committee order, header/footer, wrapping, and page breaks. Programmatic text checks are not a claim of visual layout verification.
8. Rerun those same rows: GENERATED rows must skip. For a separate deliberately failed TEST row, correct the data and verify ERROR retries; never reset successful production rows for this exercise.
9. Test an omitted Document Date; optionally test the NOC optional signatory role blank. Confirm ten dots/empty role as specified.
10. Re-run after changing only one document's configured output directory for a new TEST submission; the other two directory settings must remain unchanged. Changing a folder does not regenerate GENERATED rows.

Internet is required for the live Sheets part; fixture-based tests and local rendering do not require live Sheets access.

## 12. Future Phase 2 — document only, do not implement now

One Windows Tkinter application will create document tabs dynamically from the enabled registry entries:

```text
| NOC | Affidavit | Consent | ...future templates |
```

Each tab will have its own Browse/save directory, Generate button, Open Folder button, and result status/counts. Persist each tab's directory in that document's entry in the same active config.yaml. Do not show internal template filenames in the GUI.

Support six and later more document types by extending specs/templates/config, not copying UI or processor code. Do not create placeholder production entries for the three unspecified future templates now.

The future UI will call this backend through its result/progress interface, with background execution and main-thread GUI updates. Windows build/install paths, an external writable YAML location, packaging resources, and a new Windows environment will be decided and tested in Phase 2. Do not copy a Mac .venv to Windows or embed service-account keys into the executable.

## Final Codex response required

Report:

- files created/changed inside the permitted target folder;
- source components reused and any intentional behavior changes;
- the exact project Python executable/version and dependency setup command;
- tests actually run and their results;
- which local checks, read-only live checks, and mutating live checks were or were not performed;
- remaining user configuration actions without revealing credentials;
- exact commands for the user's three selected-row Mac tests;
- blockers and current limitations, including non-transactional file/Sheet saves;
- explicit confirmation that Tkinter/Windows work was deferred.

Do not end with a Windows/production readiness claim before the user's live and visual acceptance tests are completed.
