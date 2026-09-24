# Phase 1 extension validation — 24 September 2026

Scope: Mac/backend only. No live generation, production DOCX files, or Sheet
writes were performed. Windows code, build/installer files, desktop configuration
behavior, the three original adapters, and all six templates were left unchanged.
No legacy sibling project was modified.

## Offline milestones

| Milestone | Focused result | Complete suite |
| --- | ---: | ---: |
| Before any implementation | — | 218 passed |
| Registration | 21 passed | 239 passed |
| By-Law | 15 passed | 254 passed |
| Form-A | 93 passed | 347 passed |
| Registry/config integration | 14 passed | 361 passed |
| Captured live headers and documentation regression checks | 20 integration tests passed | 367 passed |

All tests use synthetic submissions and fake Sheets; the in-process test fixture
blocks networking. New source-execution subprocess tests also block sockets.
The header snapshot contains headings only, with no respondent values.
`pip check` reports no broken requirements. Local `validate-config` passes all
six templates, and `list-documents` reports all six keys.

## Live read-only checks and designated dry runs

Each command below ran with the project interpreter after the offline integration
suite passed. Each worksheet resolved by its exact configured title. The original
configured spreadsheet and credential reference were preserved. Authentication
used the existing credential file without printing or copying its contents.

| Key | Resolved worksheet | Mapped business headers | Missing | Ambiguous | Operational columns | Dry-run row | Result |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| registration | Registration Responses | 7 | 0 | 0 | 4/4, unique | 2 | would_generate=1 |
| by_law | By-Law Responses | 3 | 0 | 0 | 4/4, unique | 2 | would_generate=1 |
| form_a_registration | Form A Registration Responses | 59 | 0 | 0 | 4/4, unique | 2 | would_generate=1 |

All `check-sheets` commands returned exit 0. Each worksheet had one eligible
physical data row, row 2. Form-A's one nonblank completion-certificate date
matched the configured `%m/%d/%Y`; there were zero date mismatches. Registration
and By-Law contain no mapped date inputs.

```bash
.venv/bin/python main.py check-sheets --document registration
.venv/bin/python main.py check-sheets --document by_law
.venv/bin/python main.py check-sheets --document form_a_registration
.venv/bin/python main.py generate --document registration --rows 2 --dry-run
.venv/bin/python main.py generate --document by_law --rows 2 --dry-run
.venv/bin/python main.py generate --document form_a_registration --rows 2 --dry-run
```

Each dry run returned exit 0 and exactly:

```text
row 2: would_generate
generated=0, would_generate=1, skipped=0, invalid=0, failed=0, sync_failed=0, changed=0
```

Row 2 in each worksheet was selected under the user's authorization to identify
and dry-run one candidate. **None of these rows is approved for live generation.**
Do not remove `--dry-run` without explicit approval of each exact worksheet/row.

Before/after SHA-256 fingerprints of all returned Sheet headers and cell values
match for all three worksheets. This includes processing_status and every other
operational/submitted cell. The three configured production output directories
were absent both before and after the dry runs. The unchanged shared processor
rendered previews in automatically deleted temporary directories. Diagnostic logs
may be written by the existing CLI. No production DOCX was retained from live data.

## Actual heading differences and source limitations

Registration's actual address heading is `Association Address`, rather than
`Association Address / संस्था का पता` in the request. Its name heading is
`Association / Society Name / एसोसिएशन / संस्था का नाम`. These exact live wordings
are mapped explicitly. Registration and Form-A headings mostly contain trailing
spaces; the existing normalizer already handles them. There are no unresolved
mapping mismatches or missing operational columns.

Requiredness is documented in [FORM_SPEC.md](FORM_SPEC.md), with links to the
source field tables recovered from Drive. Those tables predate the user's final
combined-address revision. Removed fields were not restored. All retained
Registration fields are required; the combined address is treated as required in
place of the earlier required address components. Form-A's source table marks
association_email optional. **Current live Google Form required flags were not
independently inspected**: no browser connection was available. Confirm the final
Form still uses these requiredness rules before production acceptance.

The actual By-Law filename is `By_Law_Template.docx`. It contains 231 paragraphs,
one explicit page break and a cached Word page count of 11. The requested
one-page assertion conflicts with preserving this supplied full template. No text
or formatting was reduced to force one page. Tests verify generation, complete
address data, paragraph/run properties, page breaks, table geometry and unchanged
style resources. Current visual pagination is not certified.

Visual rendering could not run: the bundled `render_docx.py` failed because the
project interpreter lacks `pdf2image`, and LibreOffice/soffice is not installed
on the available path. No PNG/Word visual approval is claimed. This does not affect
the DOCX generation, strict-variable, ZIP/XML, content, or dynamic-table tests.

## Implementation and files

Added:
- `documents/registration.py`
- `documents/by_law.py`
- `documents/form_a_registration.py`
- `tests/extension_helpers.py`
- `tests/test_registration.py`
- `tests/test_by_law.py`
- `tests/test_form_a_registration.py`
- `tests/test_extension_integration.py`
- `tests/fixtures/extension_headers.json` (exact read-only header snapshot)
- `PHASE1_EXTENSION_VALIDATION.md` (this report)
- `local-notes/extension_live_snapshot.json` (ignored local fingerprints; no submitted values)

Modified:
- `models.py`: optional adapter hooks for dynamic placeholder inventory, synthetic
  preflight overrides, and document-specific header/row validation.
- `document_generator.py`: invokes those optional hooks while preserving defaults
  for all existing adapters, StrictUndefined, sanitization and atomic saving.
- `document_registry.py`: appends registration, by_law and form_a_registration after
  the original noc, affidavit and consent entries.
- `config.yaml` (ignored active file): adds the three requested worksheet/output
  entries and actual template names; existing settings/credential reference stay intact.
- `tests/test_documents.py`, `tests/test_processor.py`: keep the original
  three-fixture regression parametrizations explicit. All baseline cases remain;
  dedicated extension tests exercise the additional keys through the same APIs.
- `README.md`, `FORM_SPEC.md`, `IMPLEMENTATION_NOTES.md`: append extension commands,
  contracts, validation behavior, evidence and limitations while retaining history.

`processor.py`, `sheets_service.py`, `main.py`, `config_manager.py`, all original
adapters/templates, GUI/desktop files, Windows deployment/build/installer files,
and `config.example.yaml` were not modified. The latter remains the existing
Windows installer seed; portable Mac configuration additions are documented in
README and applied only to the single active config.yaml.

The shared document registry now contains, in order: `noc`, `affidavit`, `consent`,
`registration`, `by_law`, `form_a_registration`. No second processor, Sheets
service, CLI, config source, or retry/status implementation was created.

The existing desktop is registry-driven: enabled entries can become visible if
it is launched with the updated active config. No new desktop behavior was
implemented or exercised, and this is not Windows/Phase-2 acceptance.

## Exact raw live header rows

JSON strings below preserve trailing spaces. Timestamp is metadata; the last
four columns are the unchanged operational contract.

### Registration Responses

```json
[
  "Timestamp",
  "Authority Location / सक्षम प्राधिकारी का स्थान ",
  "Project Name / परियोजना का नाम ",
  "Association Address",
  "Police Station / पुलिस थाना ",
  "Association / Society Name / एसोसिएशन / संस्था का नाम ",
  "Place / स्थान ",
  "Signatory Name / हस्ताक्षरकर्ता का नाम ",
  "processing_status",
  "generated_file",
  "processed_at",
  "error_message"
]
```

### By-Law Responses

```json
[
  "Timestamp",
  "Association Name / संस्था का नाम",
  "Association Address / संस्था का पंजीकृत पता",
  "Work Area / संस्था का कार्यक्षेत्र",
  "processing_status",
  "generated_file",
  "processed_at",
  "error_message"
]
```

### Form A Registration Responses

```json
[
  "Timestamp",
  "Association Name / प्रस्तावित संस्था का नाम ",
  "Association Address / संस्था का पता ",
  "Work Area / कार्यक्षेत्र ",
  "Share Capital / अंश पूंजी ",
  "Price Per Share / प्रति अंश कीमत ",
  "Number of Members / सदस्यों की संख्या ",
  "Association Email / संस्था ईमेल ",
  "Project Name / परियोजना का नाम ",
  "Completion Certificate Number / पूर्णता प्रमाण-पत्र क्रमांक ",
  "Completion Certificate Date / पूर्णता प्रमाण-पत्र दिनांक ",
  "District / जिला ",
  "Management Committee Address / प्रबंध कार्यकारिणी का पता ",
  "Meeting Chairperson Name / बैठक अध्यक्ष का नाम ",
  "Proposed By / प्रस्ताव रखने वाले का नाम ",
  "Approved By / अनुमोदन करने वाले का नाम ",
  "Committee Member 1 Name / समिति सदस्य 1 का नाम ",
  "Committee Member 1 Designation / समिति सदस्य 1 का पद ",
  "Committee Member 1 Plot Number / समिति सदस्य 1 भूखंड क्रमांक ",
  "Committee Member 1 Mobile Number / समिति सदस्य 1 मोबाइल नंबर ",
  "Committee Member 2 Name / समिति सदस्य 2 का नाम ",
  "Committee Member 2 Designation / समिति सदस्य 2 का पद ",
  "Committee Member 2 Plot Number / समिति सदस्य 2 भूखंड क्रमांक ",
  "Committee Member 2 Mobile Number / समिति सदस्य 2 मोबाइल नंबर ",
  "Committee Member 3 Name / समिति सदस्य 3 का नाम ",
  "Committee Member 3 Designation / समिति सदस्य 3 का पद ",
  "Committee Member 3 Plot Number / समिति सदस्य 3 भूखंड क्रमांक ",
  "Committee Member 3 Mobile Number / समिति सदस्य 3 मोबाइल नंबर ",
  "Committee Member 4 Name / समिति सदस्य 4 का नाम ",
  "Committee Member 4 Designation / समिति सदस्य 4 का पद ",
  "Committee Member 4 Plot Number / समिति सदस्य 4 भूखंड क्रमांक ",
  "Committee Member 4 Mobile Number / समिति सदस्य 4 मोबाइल नंबर ",
  "Committee Member 5 Name / समिति सदस्य 5 का नाम ",
  "Committee Member 5 Designation / समिति सदस्य 5 का पद ",
  "Committee Member 5 Plot Number / समिति सदस्य 5 भूखंड क्रमांक ",
  "Committee Member 5 Mobile Number / समिति सदस्य 5 मोबाइल नंबर ",
  "Committee Member 6 Name / समिति सदस्य 6 का नाम ",
  "Committee Member 6 Designation / समिति सदस्य 6 का पद ",
  "Committee Member 6 Plot Number / समिति सदस्य 6 भूखंड क्रमांक ",
  "Committee Member 6 Mobile Number / समिति सदस्य 6 मोबाइल नंबर ",
  "Committee Member 7 Name / समिति सदस्य 7 का नाम ",
  "Committee Member 7 Designation / समिति सदस्य 7 का पद ",
  "Committee Member 7 Plot Number / समिति सदस्य 7 भूखंड क्रमांक ",
  "Committee Member 7 Mobile Number / समिति सदस्य 7 मोबाइल नंबर ",
  "Committee Member 8 Name / समिति सदस्य 8 का नाम ",
  "Committee Member 8 Designation / समिति सदस्य 8 का पद ",
  "Committee Member 8 Plot Number / समिति सदस्य 8 भूखंड क्रमांक ",
  "Committee Member 8 Mobile Number / समिति सदस्य 8 मोबाइल नंबर ",
  "Committee Member 9 Name / समिति सदस्य 9 का नाम ",
  "Committee Member 9 Designation / समिति सदस्य 9 का पद ",
  "Committee Member 9 Plot Number / समिति सदस्य 9 भूखंड क्रमांक ",
  "Committee Member 9 Mobile Number / समिति सदस्य 9 मोबाइल नंबर ",
  "Committee Member 10 Name / समिति सदस्य 10 का नाम ",
  "Committee Member 10 Designation / समिति सदस्य 10 का पद ",
  "Committee Member 10 Plot Number / समिति सदस्य 10 भूखंड क्रमांक ",
  "Committee Member 10 Mobile Number / समिति सदस्य 10 मोबाइल नंबर ",
  "Committee Member 11 Name / समिति सदस्य 11 का नाम ",
  "Committee Member 11 Designation / समिति सदस्य 11 का पद ",
  "Committee Member 11 Plot Number / समिति सदस्य 11 भूखंड क्रमांक ",
  "Committee Member 11 Mobile Number / समिति सदस्य 11 मोबाइल नंबर ",
  "processing_status",
  "generated_file",
  "processed_at",
  "error_message"
]
```
