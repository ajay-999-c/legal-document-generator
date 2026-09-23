# Windows deployment — Legal Document Generator

The desktop application reuses the tested Phase-1 processor, adapters, validation,
Sheets client and renderer. Each registry document creates one tab; Generate runs
only that document's eligible worksheet rows. No polling or automatic generation
occurs. The Windows executable must be built **on Windows**, not on macOS.

## Build machine

Use **64-bit Python 3.11** from python.org on Windows 10/11, including Tcl/Tk and
pip. This is the supported build version; the build script enforces it. Use a
current 3.11 patch release on Windows. The source GUI has been smoke-tested on
macOS with the existing project Python 3.11.0/Tk 8.6. Windows binary, installer,
Word rendering and production access still require the acceptance checks below.

From PowerShell in this project (do not reuse a Mac or sibling virtual environment):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_windows.bat
```

The batch file uses `.venv\Scripts\python.exe`, checks dependencies, runs the
complete offline suite, stops on failure, and runs the reviewed PyInstaller spec.
The resulting file is:

```text
dist\Legal Document Generator.exe
```

It is a one-file, windowed/no-console application containing Python, Tcl/Tk,
application modules, dependencies and all `templates/*.docx` files (excluding Word
lock files). The spec includes only explicit template assets and library resources;
it does not bundle the office `config.yaml`, credentials, logs, generated documents
or tests. Inspect the release artifact before distribution. A failed build may
leave an older EXE in `dist`; distribute only after the script reports success.
No Windows EXE is produced or claimed by the Mac development pass.

PyInstaller's [runtime resource rules](https://pyinstaller.org/en/stable/runtime-information.html)
and [spec-file data inclusion](https://pyinstaller.org/en/stable/spec-files.html)
are used to keep extracted templates separate from writable AppData settings.

## Install for the office user

Distribute the EXE, `install_windows.ps1`, and the **redacted** `config.example.yaml`
seed. The seed is an installation input, not a second runtime configuration. Do
not distribute the build machine's real configuration or service-account key.

If using the project's `dist` layout, run this as the intended office user in
PowerShell (administrator elevation is unnecessary):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1
```

For an EXE delivered beside the installer:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1 -SourceExe '.\Legal Document Generator.exe'
```

ExecutionPolicy Bypass here applies only to this PowerShell process. Follow office
IT policy for script approval and release signing; no policy is changed globally.
The installer does not launch the app or generate documents.

Locations:

```text
%LOCALAPPDATA%\Programs\LegalDocumentGenerator\
    Legal Document Generator.exe

%APPDATA%\LegalDocumentGenerator\
    config.yaml
    credentials.json                 # provisioned separately
    logs\
        generator.log
```

The installer creates Desktop and Start-menu shortcuts for the current user,
creates the data/log directories, and provisions the config seed only when
`config.yaml` is absent. Existing config and credentials are never overwritten,
even if `-ConfigSeed` or `-CredentialsFile` is supplied during an upgrade.

## Administrator setup

1. Open `%APPDATA%\LegalDocumentGenerator\config.yaml` in a text editor.
2. Set `google.spreadsheet_id` to the actual bare spreadsheet ID. The shipped
   placeholder is deliberately invalid, so generation cannot run until configured.
3. Keep `credentials_file: credentials.json` for the default location. Provision
   the existing service-account JSON separately; never paste private-key contents
   into YAML. An explicit absolute credential path is also supported.
4. Confirm the three existing worksheets: `NOC Responses`, `Affidavit Responses`,
   and `Consent Responses`. Preserve their input headings, operational columns,
   adapter keys, mappings and status semantics from `FORM_SPEC.md`.
5. Share the spreadsheet with the service account's email as **Editor**, using
   Google Sheets' Share dialog. An administrator obtains this email from the
   credential file securely; the app does not display it. Ensure the Google Sheets
   API is enabled for the associated Google Cloud project.
6. Confirm each `input_date_format` against actual formatted Sheet values. The seed
   uses `%m/%d/%Y`, matching the verified project pilot; do not assume another
   office's sheet uses this convention. No date guessing or Sheet reformatting occurs.
7. Keep packaged template paths relative, such as
   `templates/Affidavit_Template.docx`; they resolve inside the bundle. Absolute
   administrator template overrides still work, but are not portable between PCs.
8. Leave `output_dir: ''` for per-document defaults, or set explicit destination
   paths. On the first successful configuration load, blank/missing output settings
   are filled and persisted as `Documents\NOC Documents`,
   `Documents\Affidavit Documents`, and `Documents\Consent Documents`. Windows'
   redirected Documents location is respected. Existing explicit paths are kept,
   even if their folders have not yet been created. Generation creates them after
   backend preflight; Browse selects an existing directory.

Credentials can be provisioned at installation without including them in the release:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1 -CredentialsFile 'C:\SecureProvisioning\credentials.json'
```

Alternatively copy the credential file securely into the AppData location after
installation. Protect it using office account/filesystem access controls. Do not
store it in a shared output directory.

## First launch and normal use

Launch **Legal Document Generator** from Desktop or Start. Startup reads local
configuration only; it does not authenticate, generate files or mutate Sheets.
An invalid/missing configuration displays a concise Setup error. Have an
administrator fix the active YAML and restart. Missing credentials/templates and
remote access/schema problems are caught when generation is requested, without
crashing other tabs.

For each document:

1. Select its tab.
2. Use **Browse…** to select the exact Save Folder. No extra document subfolder is
   appended. Only this document's folder setting changes in the single YAML.
3. Click **Generate Documents** when ready to process **all eligible rows in that
   document's worksheet**. This writes files and Sheet operational cells. The GUI
   has no row selector or dry-run mode; administrators can use the existing CLI
   from a source checkout for approved selected-row diagnostics.
4. Wait for completion. All Generate and Browse buttons are disabled during the
   one active job, while tabs remain viewable. Closing is deferred until the job
   completes; forcibly killing the process may leave uncertain Sheet statuses.
5. Review Generated, Skipped and Failed counters, then **Open Generated Folder**.
   Counters describe the latest attempted batch, not historical folder contents.

Failed includes backend failed/invalid, changed rows and status-sync failures.
Generated counts only confirmed successful generation plus Sheet completion.
A sync failure can leave a saved file even though Generated is zero. The status
message flags Sheet review; detailed per-row outcomes are in logs. Skipped retains
the backend's status rules. Only blank and ERROR statuses are eligible; GENERATED,
PROCESSING and other nonempty statuses skip. No automatic retry or reset is added.

Use only one application/process/machine (including the CLI and legacy programs)
against a worksheet at a time. The GUI prevents overlapping jobs within its own
window; it does not provide a distributed lock or a machine-wide instance lock.
Do not sort, insert or delete rows while a batch runs. File saving and Sheet status
updates are not a transaction; review uncertain rows/files before any retry.

## Upgrades

1. Wait for the active job to finish and close the application.
2. Back up the user's active config and credentials securely, and retain any
   required generated documents.
3. Build/test the new version on Windows and distribute the new EXE plus installer.
4. Run the same install command as the same office user. The installer refuses if
   an application process is still running and stages the EXE before replacement.
5. Confirm existing `config.yaml`, credentials and selected output directories
   remain unchanged, then launch and perform the local acceptance checks.

The installer never silently migrates settings or replaces credentials. If a new
release adds a document, the administrator adds its reviewed entry to the existing
YAML; old settings are not replaced with the seed. Adding a document requires an
adapter, registry entry, template and YAML entry, with no new tab implementation.

## Logs and troubleshooting

Default logs: `%APPDATA%\LegalDocumentGenerator\logs\generator.log`. Logs rotate
at approximately 2 MB, retaining four backups. GUI logs always stay in the
application data directory on Windows, even when upgrading a config containing a
legacy absolute log path; its basename is retained. Source execution on Mac uses
the configured log path. Startup errors use the default log until settings load.

Logs include document key, start/end, destination, processing counts, row outcomes,
safe backend diagnostics and status synchronization errors. Unexpected exceptions
record type and stack locations without copying exception payloads, locals,
credential contents or cloud responses into logs. If the log directory itself
cannot be written, startup reports Setup error; check the directory's permissions.

| Symptom | Administrator action |
| --- | --- |
| Setup error on launch | Check the AppData config exists, YAML syntax/unique keys, actual spreadsheet ID, distinct per-document destinations and worksheets. Restart after edits. |
| Setup error on Generate | Check credential-file presence/validity, Google Sheets API enablement, sharing and exact worksheet name. Inspect exception type/location in logs. |
| Missing template | Reinstall the correct build; preserve the relative template paths in YAML. Do not copy an absolute Mac path to Windows. |
| Invalid headings/mapping | Compare existing worksheet headings with `FORM_SPEC.md`; do not alter adapters to guess fields. |
| Could not save folder | Select an existing accessible folder distinct from other enabled documents; check config write permissions. The prior setting remains on a failed save. |
| Output/save failure | Check destination permissions, network drive availability, free space and whether Word has locked the target file. |
| Row failed | Review the safe row diagnostic and source values; correct data, then deliberately retry eligible ERROR rows. |
| Sheet updates need review | A local file may exist or a PROCESSING claim may be uncertain. Reconcile files and Sheet status before retrying; never automatically reset statuses. |
| Open folder fails | The folder may not exist before first generation; select/create an accessible directory. |
| Configuration edited while open | Restart before generating so displayed folders and processor settings agree. |
| Window cannot close | Allow the active request/batch to finish. Cloud read retries/timeouts are bounded by the existing backend. |
| Windows blocks EXE/script | Follow IT signing/allowlisting procedures; inspect build provenance and security alerts. |
| Missing DLL/Tk or immediate launch failure | Rebuild with Python 3.11 x64 and requirements-build.txt; inspect PyInstaller warnings and test on a clean Windows machine. |

## Required Windows acceptance before office rollout

- Build with `build_windows.bat`; confirm the full offline suite passes on Windows.
- Install under a standard user; verify both shortcuts, no console, bundled
  templates, redirected Documents defaults and AppData config/log locations.
- Test missing/invalid config, missing credentials, read-only config/output paths,
  canceled Browse, paths with spaces/Hindi characters and unavailable network drives.
- Verify all three tabs, independent folder persistence after restart, responsiveness,
  one-job guard and close-during-job behavior. Use the source smoke script first:
  `.\.venv\Scripts\python.exe scripts\smoke_gui.py` (fake processor, no cloud).
- Inspect bundle contents for secrets and confirm startup works without network.
- Verify installation/upgrade preserves config and credentials byte-for-byte,
  including when seed/credential arguments are supplied again.
- With explicit authorization and designated test submissions, verify real Sheets
  access, generation, status synchronization, retry/skip behavior and saved files
  for each document. Never use unapproved production rows as a smoke test.
- Open output DOCX files in the office's Microsoft Word installation to verify
  Hindi fonts, line wrapping, pagination, headers and printing.

## Source development on Mac

```bash
.venv/bin/python app.py
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/smoke_gui.py
```

Source mode uses the project's `config.yaml` without changing the CLI's paths or
behavior. The display-required smoke script uses only synthetic temporary settings
and a fake processor. Normal `app.py` generation is live only after a user clicks
Generate. Do not run the Windows build on Mac.
