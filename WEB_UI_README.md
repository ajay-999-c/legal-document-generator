# Local web UI with Google Sheets storage

This additive FastAPI + Jinja2 + Bootstrap 5 UI stores canonical projects, members and committee assignments in Google Sheets. It reuses the existing Google connection settings, service-account credentials, document adapters and DOCX templates. Generate returns a browser attachment: one DOCX for a project document, or a ZIP containing a personalized DOCX for every member. Rendering happens in memory; the web flow does not use the generated/ output folder or change legacy response rows/statuses. The legacy CLI folder workflow remains available for testing; the Tkinter GUI and desktop packaging have been removed.

## Run locally

From `legal-document-generator/`, use the existing project virtual environment:

```sh
.venv/bin/python -m pip install -r requirements-web.txt
.venv/bin/python -m web.sheets_repository init
.venv/bin/python -m web.app
```

Open **http://127.0.0.1:8000**. The normal launch uses Google Sheets; look for the GOOGLE SHEETS badge. `init` creates only absent UI tabs and verifies existing headings; it is safe to repeat and does not seed mock data. Stop with Ctrl+C. For development with automatic reload:

```sh
.venv/bin/python -m uvicorn web.app:app --reload --host 127.0.0.1 --port 8000
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

Run one process/worker. This is a local, unauthenticated prototype; do not expose it publicly. Bootstrap 5.3.3 CSS is vendored under `web/static/vendor/`, including its license header, so no CDN or internet connection is needed at runtime. There is no frontend build step, JavaScript, or HTMX dependency; ordinary HTML forms handle saves through redirects and generation through attachment responses. The browser stays on the current page during a download; refresh to see updated generation badges.

## Approved contract

The requested `MASTER_UI_VARIABLES.md` is not present in this checkout. The matching approved “Canonical UI Variables” contract is **`mater_ui_variables.md`**. It is used as the source of truth and left unchanged. `web/schema.py` defines only its canonical inputs; backend placeholder aliases are not exposed as form fields.

The only date field is `completion_certificate_date`. New projects start with an empty certificate date. All legal document dates remain handwritten; there are no document-date defaults. The fixture's certificate date is a fixed, obviously synthetic example.

Future formatting requirement, deliberately deferred: **Affidavit body 12.5 pt; Consent body 12.5 pt.** No DOCX templates were modified.

## Structure

- `web/app.py`: app factory, static files, local server entry point, local-host checks and storage-error pages.
- `web/routes/ui.py`: page and form handlers using Jinja2 templates.
- `web/schema.py`: canonical fields, bilingual labels, groups, document names.
- `web/repository.py`: `Project`, repository protocol, storage/conflict exceptions and in-memory demo implementation.
- `web/sheets_repository.py`: normalized Sheets persistence, explicit initialization/check commands, conflict detection and readback verification.
- `web/mock_data.py`: one fictional test project, five members, five committee assignments.
- `web/services.py`: readiness and resolving committee/president values.
- `web/downloads.py`: canonical-to-adapter mapping, in-memory DOCX/ZIP rendering and attachment responses.
- `web/templates/`: base navigation, reusable field/document-card macros, dashboard, overview, project form, members, member form/detail, committee, documents and 404 page.
- `web/static/`: local Bootstrap CSS and small responsive office-style overrides.
- `requirements-web.txt`: optional web dependencies, separate from backend dependencies.
- `tests/test_web_ui.py`: isolated offline UI and workflow tests.
- `tests/test_web_sheets.py`: offline Sheets transport, persistence, conflict/failure and live-mode form tests.

The app receives its repository through `create_app(repository=...)`. `create_app()` defaults to a fresh demo repository for offline tests; the exported ASGI `app` and normal CLI default to Sheets. Authentication is lazy, and startup never creates tabs. There is no silent fallback to demo data when Sheets is unavailable. POST cloud calls run in the thread pool. Document rendering also runs in the thread pool and uses the existing strict adapter validation. Affidavits require an assigned member designation; missing data blocks the batch before download.

## Screens and routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/`, `/projects` | Searchable project dashboard |
| GET, POST | `/projects/new` | Create a project |
| GET | `/projects/{project_id}` | Project overview and document summary |
| GET, POST | `/projects/{project_id}/details` | Shared project and document-specific details saved together; committee assignment controls are on Members |
| GET | `/projects/{project_id}/members` | Search, select and browse members |
| GET, POST | `/projects/{project_id}/members/new` | Add member |
| GET | `/projects/{project_id}/members/{member_id}` | Member details, reused values, document controls |
| GET, POST | `/projects/{project_id}/members/{member_id}/edit` | Edit the shared member record |
| POST | `/projects/{project_id}/members/generate` | Download a ZIP of Affidavits or Consent letters for all project members |
| GET, POST | `/projects/{project_id}/committee` | GET redirects to Members; POST adds or updates member-role assignments |
| POST | `/projects/{project_id}/committee/{member_id}/remove` | Remove assignment; preserve member record |
| GET | `/projects/{project_id}/documents` | Project/member document groups and settings |
| POST | `/projects/{project_id}/documents/settings` | Save canonical document settings |
| POST | `/projects/{project_id}/documents/{kind}/generate` | Generate/regenerate and download a project DOCX |

Project document keys are `noc`, `registration`, `by_law`, `form_a`; member keys are `affidavit`, `consent`. GET requests do not mutate state.

## Storage and configuration

Three dedicated tabs in the configured spreadsheet hold the canonical data:

| Tab | Content |
| --- | --- |
| `UI Projects` | Stable project ID, project/association fields and document-specific settings |
| `UI Members` | Project ID, stable member ID and the six member fields |
| `UI Committee` | Project ID, member ID, designation and ordering position |

The six existing response tabs remain independent. Existing response rows are **not** automatically imported or merged into projects. The Sheets workspace starts empty; create your first project through the UI. No demo or client records are embedded in storage setup.

The existing `config.yaml` supplies only `google.spreadsheet_id` and `google.credentials_file`; it is never rewritten. The already shared service account needs Editor access. Optional environment variables:

- `LEGAL_WEB_CONFIG`: alternate configuration file path.
- `LEGAL_WEB_SPREADSHEET_ID`: use a different, already shared spreadsheet without changing the backend config.
- `LEGAL_WEB_STORAGE=demo`: run the original in-memory fixture with no Sheets connection.

```sh
# Read-only connection/schema/data check
.venv/bin/python -m web.sheets_repository check

# Offline mock UI (changes reset on restart)
LEGAL_WEB_STORAGE=demo .venv/bin/python -m web.app
```

Storage uses literal text cells, preserving leading zeroes, Hindi and certificate identifiers. It validates exact headers and relational IDs; formulas and numeric/date-coerced cells in UI tabs are rejected rather than silently converted. Prefer editing through the UI, and do not change the UI-tab headings or column layout. Each tab supports up to 10,000 rows, growing as needed. This small-office repository reads only its three bounded UI tabs; it is not designed for large-scale data access.

Each save rereads the stored project, checks a content revision, updates the affected project/member/committee rows in a single atomic Sheets batch, and reads them back. Forms include a hidden revision so a stale browser tab cannot silently overwrite a newer edit. Writes are not automatically retried after an ambiguous failure. The UI shows a clear error and asks the operator to reload/check records; it never reports an unconfirmed save as successful. Generation badges remain local to the running process and never enter Sheets.

Use a single web process. An in-process lock serializes repository writes, but Sheets does not provide compare-and-swap transactions: simultaneous external edits or multiple servers can still race between the check and the batch. Do not sort, move or edit the UI tabs while saving in the app. This limitation does not affect the existing response-tab workflows.

The atomic batch behavior follows the [Google Sheets API contract](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate); it is not a database transaction across concurrent editors.

## Try the workflow

1. Create a project and review its details. In offline demo mode, you can instead open the sample project.
2. Open a member, edit the name or plot, and verify the Committee and member document pages reuse the changed values.
3. In the Committee section of Members, choose an existing member and designation. Selecting an already assigned member updates their role. Only one अध्यक्ष can be assigned; remove or change the previous assignment to replace the president.
4. Review Documents. NOC recipient comes from the developer; signatory comes from अध्यक्ष. No manual NOC person inputs exist.
5. On Members, generate Affidavit or Consent for all project members without selecting rows. Search does not limit the batch. If any member needs more data, the batch stops before rendering so nobody is silently omitted. Individual member pages show readiness and link back to the all-member action.
6. Edit document-specific details in Project Details, save once with the shared project information, and try Generate/Regenerate on project cards. The browser downloads a DOCX attachment immediately. Members download as a ZIP. Downloads use the browser’s normal save preferences.
7. Restart the server: Sheets records remain available. Only session generation badges reset.

Normal members can be saved before all document details are available. Readiness checks require father/age for Affidavit, address/plot for both member documents, and 5–11 committee members for Consent and 3–11 for Form-A. Form-A also needs committee mobiles/plots and a declared member count covering the committee. The declared Form-A member count remains distinct from the number of entered member records. Committee order is assignment order; the first assignment supplies future Form-A first-signatory details, matching the existing adapter.

Project records persist in Sheets and are shared by browser tabs. In explicit demo mode, records live only in memory and restarting resets the fixture. Changes conservatively clear that project's generation badges to avoid presenting old results as current. This rule belongs only to the prototype; production retry/status rules are unchanged. The readiness checks are for UI validation, not a production/legal validation service.

## Validation

```sh
.venv/bin/python -m pytest tests/test_web_ui.py tests/test_web_sheets.py -q
.venv/bin/python -m pytest tests -q
.venv/bin/python -m pip check
```

Sheets integration verified: **54 web tests passed; full suite 516 passed** (35 original UI tests plus 19 Sheets tests). One dependency deprecation warning concerns Starlette's use of the AnyIO BlockingPortal alias. `pip check` reports no broken requirements.

Tests cover startup, all pages, canonical fields exactly once, the sole certificate date input, absence of person aliases/date duplicates, reference-only committee assignments, searching, project/member creation and edits, validation, escaping, president uniqueness, readiness, single DOCX/bulk ZIP downloads, regeneration, invalid member IDs, repository isolation, and isolation from desktop processing and output storage. Existing network-blocking test fixtures remain active.

The local server starts successfully. Interactive visual review was attempted, but the host's macOS screen-capture service failed; browser layout review remains to be performed by opening the URL above.

During the original UI phase, all 78 pre-existing files in the source/config/template snapshot were verified byte-for-byte unchanged. Existing uncommitted changes to `templates/Affidavit_Template.docx` and `tests/test_desktop.py` were present before this task and preserved. The registry, adapters, processor, generator, all six templates, CLI, Tkinter, Windows packaging, configuration, credentials, and existing tests were not edited. The Sheets integration initializes and reads back only its three dedicated UI tabs. No legacy response cells or production generation statuses are written.

## Load previous projects from response sheets

Use **Projects → Load Previous Project → Review and load**. This explicitly reads the six configured response worksheets, regardless of their generation status; it does not change their rows, statuses or headings. Search by project or association. The review screen shows the source sheet/row references, shared details, document settings, proposed members and committee assignments. Clicking **Load project into workspace** saves the reviewed canonical copy into the three UI tabs.

- Projects are grouped by normalized exact project name **and** association name. Different spellings are not guessed or fuzzily merged.
- By-Law has no project-name input; its association-only row is attached only when exactly one discovered project has that association.
- Member records match by name and plot; a name-only committee record joins only a unique matching member. Ambiguous matches remain separate for review. Missing or conflicting personal fields are shown in the preview and remain blank for completion in Members.
- Conflicting project/settings values are listed with their sources and left blank. The operator can enter the correct canonical value during review. Only the completion certificate date is imported, parsed using that source document's configured date format; other legal dates and old generated statuses are never imported.
- The committee is assigned only when the source rosters resolve consistently to valid member references and designations. Otherwise members are retained and committee roles must be assigned after loading.
- The POST rereads the response data and rejects a changed source fingerprint. Stable import IDs prevent repeat loads from creating duplicates. An already loaded project, or a single saved project with the same normalized project name, is opened without overwriting later edits.
- The source reader is deliberately read-only. Import writes use the existing checked Sheets repository. A lost write response is not automatically retried; reopening the loader finds the deterministic project ID if the import succeeded.
- Missing source tabs/headings are reported. Duplicate recognized headings or oversized sources fail clearly rather than guessing. Reads use formatted strings in bounded ranges to preserve identifiers as represented in Sheets.

New routes: `GET /projects/load`, `GET /projects/load/{key}`, `POST /projects/load/{key}`. Implementation: `web/legacy_import.py`, `web/routes/imports.py`, two Jinja templates, and `web/legacy_fields.json` (read-only header snapshot verified against the production adapter definitions by tests). No existing adapter imports or changes are introduced into the web runtime.

Run the import tests with `.venv/bin/python -m pytest tests/test_web_import.py -q`. The live acceptance check only discovers and previews source records; importing a particular project is left to the operator's review screen.

Previous-project loader validation: **69 web tests passed; full suite 531 passed**, with the same dependency deprecation warning. Live read-only discovery found three project/association groups and displayed source conflicts for review. No historical project was imported during verification.

## Tehsil naming

The canonical field is `tehsil`, labelled **Tehsil / तहसील**. New `UI Projects` sheets use `tehsil` in column N. Existing `authority_location` headers remain readable and writable without changing stored values. Legacy Affidavit/Registration response headings are accepted as aliases; their existing DOCX placeholder names are retained.

Developer details now have three separate fields: `developer_name`, `developer_address`, and `developer_company`. NOC readiness requires the company as well as the person and address. Historical NOC company values import into `developer_company`, never into the person name. Existing UI Projects sheets must insert `developer_company` after `developer_address` (column J); the new schema has 26 columns A:Z.

## Unique project names

Project name is the unique business key for create, edit and import. Comparison ignores case, leading/trailing and repeated whitespace, and canonically equivalent Unicode. Internal `project_id` remains stable for member references and URLs, including when a project is renamed. Duplicate create/rename submissions return a 409 form error without overwriting the existing project. Import opens the existing same-name project even if its association differs. Repository checks run inside the write lock, preventing simultaneous duplicate saves in the supported single-process app. Google Sheets does not enforce a unique constraint: direct sheet edits and independent app processes are outside this guarantee. Existing duplicate records are not automatically deleted or merged; they remain available for review. No new sheet columns are needed.

## Builder NOC

Builder NOC is the seventh web document type (five project types plus Affidavit and Consent). It appears on the project overview and Documents page. `POST /projects/{project_id}/documents/builder_noc/generate` uses the existing project handler to download `builder_noc_{safe_project_name}.docx` in memory, without writing to the generated folder.

`documents/builder_noc.py` validates these existing `UI Projects` fields and maps each to its identically named template placeholder: `developer_company`, `developer_address`, `developer_name`, `tehsil`, `district_name`, `association_name`, `project_name`, `association_address`, `rera_registration_no`, `completion_certificate_no`, and `completion_certificate_date`. The certificate date uses the existing ISO-to-DD-MM-YYYY formatting. `association_address` supplies the complete location/Khasra text as entered. No committee or member record is required.

`templates/Builder_NOC_Template.docx` is used unchanged, including its printed `दिनांक:------------` line. No `document_date`, form fields, Sheet columns or separate response worksheet are added. The web registry extends the existing six adapters locally, leaving CLI and legacy import contracts unchanged.
