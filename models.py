"""Small public contracts shared by CLI, adapters, and future desktop UI."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


class SetupError(ValueError):
    """Configuration, template, or worksheet schema requires operator attention."""


class RowError(ValueError):
    """Safe field-oriented diagnostic; never includes a submitted value."""


@dataclass(frozen=True)
class Field:
    parameter: str
    heading: str
    placeholder: str
    required: bool = True
    kind: str = 'text'
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentSpec:
    key: str
    version: str
    fields: tuple[Field, ...]
    context_builder: Callable[[dict[str, str]], dict]
    template_check: Callable[[dict[str, str]], None] | None = None
    # Dynamic adapters may declare loop expressions separately from flat inputs.
    template_placeholders: frozenset[str] | None = None
    preflight_values: tuple[tuple[str, str], ...] = ()
    header_check: Callable[[list[str]], None] | None = None
    row_check: Callable[[dict[str, str]], None] | None = None


@dataclass(frozen=True)
class DocumentSettings:
    key: str
    enabled: bool
    label: str
    worksheet_name: str
    template_path: Path
    output_dir: Path
    filename_pattern: str
    input_date_format: str


@dataclass(frozen=True)
class Settings:
    config_path: Path
    spreadsheet_id: str
    credentials_file: Path
    scopes: tuple[str, ...]
    app_name: str
    log_file: Path
    log_level: str
    document_date_format: str
    processed_at_format: str
    blank_document_date: str
    error_message_max_length: int
    documents: dict[str, DocumentSettings]


@dataclass
class RowOutcome:
    row_number: int
    outcome: str
    message: str = ''
    saved_path: Path | None = None
    synchronization_errors: list[str] = field(default_factory=list)


@dataclass
class BatchResult:
    document_key: str
    dry_run: bool
    rows: list[RowOutcome] = field(default_factory=list)

    @property
    def counts(self):
        names = ('generated', 'would_generate', 'skipped', 'invalid', 'failed', 'sync_failed', 'changed')
        return {name: sum(row.outcome == name for row in self.rows) for name in names}

    @property
    def successful(self):
        return not any(self.counts[k] for k in ('invalid', 'failed', 'sync_failed', 'changed'))
