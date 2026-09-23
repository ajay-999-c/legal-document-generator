# Legal Document Generator

Shared backend, CLI and Tkinter desktop application for the existing NOC, Affidavit, and Consent Forms. Each document uses its own worksheet and output directory in one spreadsheet. The current business contract is [FORM_SPEC.md](FORM_SPEC.md), regenerated on 23 September 2026. No legacy application is imported at runtime.

| Key | Worksheet | Inputs | Required | Optional |
| --- | --- | ---: | ---: | --- |
| `noc` | `NOC Responses` | 14 | 12 | Document Date, Signatory Role |
| `affidavit` | `Affidavit Responses` | 17 | 16 | Document Date |
| `consent` | `Consent Responses` | 24 | 23 | Document Date |

The Tkinter desktop application now adds registry-driven NOC, Affidavit and Consent tabs on this shared backend. Run `.venv/bin/python app.py` from source. Each tab persists its own Save Folder in `config.yaml`; Generate runs only that document in a worker, with one job per application window. Startup performs no Sheets operations. Templates and administrator settings stay out of the office UI.

See [Windows deployment](WINDOWS_DEPLOYMENT.md) for build, installation, configuration, credentials, upgrades and acceptance checks. Windows packaging infrastructure is provided; the Windows executable and installer still require testing on Windows. Automatic polling and scheduled generation are not implemented.

## Environment and offline tests

Run from `jobmitra/legal-document-generator/`. Always use this project's interpreter. Tested on macOS with Python **3.11.0**. If `.venv` does not exist, create it once with a compatible Python 3.11+ interpreter; do not reuse a sibling environment.

```bash
python3 -m venv .venv
.venv/bin/python -c 'import sys; print(sys.executable); print(sys.version)'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest tests -q
.venv/bin/python main.py list-documents
```

Skip the `venv` creation command when the project environment already exists. The implementation environment is `/Users/mac/python/jobmitra/legal-document-generator/.venv/bin/python`. Direct package versions are pinned in the project's single `requirements.txt`; transitive dependencies are resolved by pip. No global or sibling packages are required.

Tests use synthetic fixtures, fake Sheets, socket blocking and temporary output directories. They render the actual target DOCX templates and inspect text, indexed committee entries, Word headers and unchanged style resources. These checks do not establish visual page-layout quality; opening the live test outputs is a separate acceptance step.

## One runtime configuration

`config.yaml` is the only active runtime settings source. A placeholder file was created for local setup and is ignored by Git. Fill in the actual bare spreadsheet ID. A full Google Sheets URL is rejected. Keep the existing service-account JSON separate at `credentials.json` or another secured path referenced by YAML. Do not put private keys into YAML or commit credentials. `credentials.json`, `secrets/`, local config, environments, generated files and logs are ignored.

The user must provision the secret; the application never creates/copies a key. File presence does not prove the key is valid or the service account has access. Grant that existing service account Editor access to the common spreadsheet through the normal administrator process. A read-only command cannot prove write permission.

Redacted complete example (documentation only; keep the active settings in `config.yaml`):

```yaml
schema_version: 1
app:
  name: Legal Document Generator
  log_file: logs/generator.log
  log_level: INFO
google:
  spreadsheet_id: YOUR_SPREADSHEET_ID
  credentials_file: credentials.json
  scopes:
    - https://www.googleapis.com/auth/spreadsheets
formatting:
  document_date_format: '%d-%m-%Y'
  processed_at_format: '%d-%m-%Y %H:%M:%S'
  blank_document_date: '..........'
processing:
  error_message_max_length: 500
documents:
  noc:
    enabled: true
    label: NOC
    worksheet_name: NOC Responses
    template_path: templates/Noc_Template.docx
    output_dir: generated/noc
    filename_pattern: NOC_{project_name}_{recipient_name}_{row_number}.docx
    input_date_format: '%Y-%m-%d'
  affidavit:
    enabled: true
    label: Affidavit
    worksheet_name: Affidavit Responses
    template_path: templates/Affidavit_Template.docx
    output_dir: generated/affidavit
    filename_pattern: AFFIDAVIT_{name}_{row_number}.docx
    input_date_format: '%Y-%m-%d'
  consent:
    enabled: true
    label: Consent
    worksheet_name: Consent Responses
    template_path: templates/Consent_Template.docx
    output_dir: generated/consent
    filename_pattern: CONSENT_{project_name}_{applicant_name}_{row_number}.docx
    input_date_format: '%Y-%m-%d'
```

The default YAML path is beside `main.py`, regardless of the current directory. `--config /path/to/config.yaml` chooses one alternate active file; there is no merge/fallback settings source. Every relative YAML path is resolved against that file's parent. Absolute paths, spaces and `~` are supported. `output_dir` is the final directory; the backend does not append another document subfolder. Enabled types must use distinct worksheets and distinct output directories. Changing one output directory does not change the other two.

Schema version, formatting values, scope and operational names are checked against the agreed contract. Duplicate YAML keys, malformed IDs, missing settings, unsupported enabled adapters and unsafe filename patterns are rejected. Patterns may use that adapter's snake_case fields plus `row_number`; `row_number` is mandatory and `.docx` is required. Attribute access, conversions, format specifiers and path traversal are rejected. Missing templates for unrelated document types do not block generation of the selected type.

## Dates and identifiers

The initial `%Y-%m-%d` input format is an example, not an assertion about your Sheet. Confirm the actual formatted strings returned by Sheets. Configure each document's `input_date_format` explicitly: `%Y-%m-%d`, `%d-%m-%Y`, `%m/%d/%Y`, `%d/%m/%Y`, `%m/%d/%y` or `%d/%m/%y`. No month-first/day-first guessing or live date-format mutation occurs. An ambiguous slash date can match both conventions; the operator must confirm which convention the worksheet uses. Invalid dates produce field-oriented row errors. Every completion-certificate date is required. Blank Document Date prints ten dots; valid dates print `DD-MM-YYYY`.

All Sheet cells are read as formatted strings rather than numericised records. Submitted `026` and `343/1` remain text through validation and rendering. If Sheets has already discarded leading zeroes, this backend cannot reconstruct them; verify the original Form/Sheet transport using designated test submissions. Age alone is validated as an integer from 1 to 120. Plot, Khasra, RERA and certificate identifiers have no numeric-only restriction.

The NOC address's old heading is an explicit alias. Affidavit supports both `Father’s Name` and the reviewed straight-apostrophe `Father's Name` label. Other wording changes are not guessed. The old combined Affidavit land/location heading is deliberately not accepted: historical rows require the separate Khasra and Project Location fields. All document headings must exist, including columns with optional answers. Duplicate headings resolving to one input are rejected.

## Current Mac pilot check

With the user-provided credentials and spreadsheet ID, read-only checks passed for all three worksheets. The current stored certificate dates matched month/day/year unambiguously; the active YAML now uses `%m/%d/%Y` for each document. The redacted example above deliberately remains an example. Nonblank Document Date transport still needs a designated test because the inspected Document Date cells are blank.

Selected-row dry runs passed for **NOC Responses row 3**, **Affidavit Responses row 2**, and **Consent Responses row 2**. The dry runs made no persistent documents or Sheet writes. The user then explicitly approved generation for these exact rows: all three commands completed with generated=1, no failures and no synchronization errors. Three DOCX files were saved in the configured directories; their ZIP/XML and placeholder checks passed. Visual inspection and the subsequent skip/retry acceptance checks remain pending. Do not reuse these row numbers for unrelated future submissions.

## CLI commands and exits

```bash
.venv/bin/python main.py list-documents
.venv/bin/python main.py validate-config
.venv/bin/python main.py check-sheets --document noc
.venv/bin/python main.py check-sheets --document affidavit
.venv/bin/python main.py check-sheets --document consent
```

- `list-documents` reports local registered schemas without loading configuration or contacting Google; it labels this distinction from configured enabled state.
- `validate-config` validates local schema first, then reports each enabled template and credential-file presence separately. It neither opens the credential JSON nor authenticates. Destination write access is checked only before real generation. Invalid global configuration must be fixed before document diagnostics can run.
- `check-sheets` is read-only. It checks the selected template and exact worksheet headers, reports physical-row/status counts and configured-date match counts without displaying personal values. Date mismatches return exit 1. Matching ambiguous dates still need operator confirmation.
- `generate --dry-run` uses the same mapping/validation and renders eligible selected rows only to automatically removed temporary directories. It writes no Sheet cells and leaves no generated DOCX in the configured directory. A small configured diagnostic log can be written. Results are `would_generate`, `invalid`, `skipped`.
- `generate` without `--dry-run` is a mutating operation. It writes local DOCX files and the selected rows' operational cells. `--rows 12,18` refers to physical Sheet row numbers, not submission IDs. Row 1 and invalid numbers are rejected; duplicates are deduplicated. Selecting a row does not override its status.
- Omitting `--rows` processes the entire eligible batch of that one selected document. Do this only deliberately after the pilot. There is no generate-all or force-generated option.

Exit codes: **0** successful command/batch (including only skipped rows); **1** row failures, invalid dry-run rows, detected changes, synchronization failures, or date diagnostic mismatches; **2** setup/schema/connection failures or invalid CLI arguments.

## Manual Mac live acceptance

Use the three existing Forms. Do not recreate Forms, move historical data, reset production statuses or rename worksheets through this application. Each linked worksheet must already have its exact Form headings and the four operational columns:

```text
processing_status
generated_file
processed_at
error_message
```

1. Provision the credential file and spreadsheet ID in `config.yaml`. Verify worksheet names and output directories. Run `validate-config` and the three read-only `check-sheets` commands above. Confirm the date convention; correct configuration rather than guessing.
2. Submit a clearly identified TEST response in each existing Form. Record its actual physical worksheet row. The rows need not be 2 or equal across the worksheets. If asking Codex to run generation, provide and explicitly approve the exact spreadsheet/worksheet/row scope first.
3. Set the following shell variables to the approved rows. The deliberate placeholders below fail CLI validation until replaced; they cannot accidentally select row 2.

```bash
NOC_TEST_ROWS='REPLACE_WITH_APPROVED_NOC_ROW'
AFFIDAVIT_TEST_ROWS='REPLACE_WITH_APPROVED_AFFIDAVIT_ROW'
CONSENT_TEST_ROWS='REPLACE_WITH_APPROVED_CONSENT_ROW'

.venv/bin/python main.py generate --document noc --rows "$NOC_TEST_ROWS" --dry-run
.venv/bin/python main.py generate --document affidavit --rows "$AFFIDAVIT_TEST_ROWS" --dry-run
.venv/bin/python main.py generate --document consent --rows "$CONSENT_TEST_ROWS" --dry-run
```

4. Inspect those dry-run results. After approval, run each selected document sequentially:

```bash
.venv/bin/python main.py generate --document noc --rows "$NOC_TEST_ROWS"
.venv/bin/python main.py generate --document affidavit --rows "$AFFIDAVIT_TEST_ROWS"
.venv/bin/python main.py generate --document consent --rows "$CONSENT_TEST_ROWS"
```

5. Confirm the three files are in the three configured directories. Confirm only those rows' operational cells changed, with correct filenames, local-clock processed times and cleared errors. No submitted fields or Timestamp should change.
6. Open each DOCX in Word or another suitable Mac viewer. Inspect all supplied values, Hindi, wrapping/page breaks, blank/filled dates, association-name city suffix, the separate Affidavit land/location sentence, and all five Consent members in order. Inspect Consent's society address in the header. Programmatic tests do not replace this visual review.
7. Repeat the same three generation commands: GENERATED rows must skip. Use a separate deliberately invalid TEST row for ERROR/retry testing; correct its data and retry. Do not reset successful production rows. For stale PROCESSING rows, inspect the local file and status history before any manual reset.
8. Make new TEST submissions with Document Date omitted, and optionally omit NOC Signatory Role. Confirm ten dots and the blank role. Change only one document's configured output directory and generate a new TEST submission; verify the other two directory settings remain unchanged. Changing a folder does not regenerate GENERATED rows.

## Status and failure behavior

Trim and uppercase statuses. Only blank and ERROR are eligible; PROCESSING, GENERATED and other nonempty statuses skip. A failed row is attempted once per invocation, not retried in a loop. Truly empty non-submission rows skip while retaining physical row numbering.

Preflight checks the selected template's complete placeholder inventory, strict synthetic context render, destination access and worksheet schema before changing statuses. A row/header snapshot is re-read before claiming the row. Changed data/status/headings cause `changed` with no writes to that row. Read failures before a claim also cause no writes. This is change detection, not an atomic lock.

A confirmed claim writes PROCESSING and clears the old error. An uncertain PROCESSING write produces `sync_failed` without generating a file; inspect the row manually. Validation/render/save failures after a claim attempt ERROR plus a concise error (at most the configured 500-character ceiling) and processing continues. These errors do not contain submitted values.

Files are saved via a temporary file in the output directory followed by replacement of the final deterministic target. After a successful save, the four operational fields are sent in one RAW values batch: GENERATED, basename, local timestamp, empty error. A success-write failure reports the saved local path separately, attempts ERROR, and reports any additional ERROR-write failure. It is never counted as a fully generated/synchronized row. Existing filename/time cells are not cleared on an error.

Read retries are bounded at three attempts for connection/timeouts and HTTP 429/500/502/503/504, with short backoff; connection/read timeouts are 15/60 seconds. Writes are attempted once because a transport failure may conceal an applied write. No generation is retried automatically in the same invocation. The implementation uses formatted-value reads and RAW status writes as documented by [gspread](https://docs.gspread.org/en/master/api/models/worksheet.html) and [Google Sheets values API](https://developers.google.com/workspace/sheets/api/guides/values).

File save and Sheet status update are **not one transaction**. Retrying the same row and filename can replace an existing local file. Changed names/configuration may leave an older file alongside a new one. Sheet row numbers are not permanent identifiers. Run only one process/machine/legacy app against a given worksheet, and do not sort, insert, delete or move rows while processing. Exactly-once generation is not guaranteed across row moves, concurrent workers or lost status updates.

## Backend extension interface

`run_batch(settings, document_key, rows=None, dry_run=False, worksheet=None, progress=None)` returns `BatchResult` with per-row outcomes, counts, saved paths and synchronization errors. An optional callback receives each `RowOutcome`; callback failure is logged without aborting document processing. The desktop calls this interface without importing any GUI code into the backend.

Adding a new document requires a versioned adapter/field contract, template, explicit registry entry and YAML entry. The shared processor and CLI generation path contain no per-document branches. The desktop application uses this same extension interface. Its generic tab component requires no document-specific UI functions; packaging includes templates explicitly, and the installer preserves existing runtime settings.
