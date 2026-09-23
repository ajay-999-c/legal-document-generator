"""One sequential workflow for any registered document adapter."""
from datetime import datetime
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from document_registry import selected
from document_generator import (clean, preflight_template, preflight_destination,
    validate_values, render_bytes, output_filename, save_atomic)
from models import BatchResult, RowOutcome, RowError, SetupError
from sheets_service import connect, snapshot, unchanged, update_operations

logger = logging.getLogger('legal_generator')


def run_batch(settings, document_key, rows=None, dry_run=False, worksheet=None, progress=None):
    spec, config = selected(settings, document_key)
    preflight_template(spec, config, settings)
    if rows is not None and (not rows or any(type(n) is not int or n < 2 for n in rows)):
        raise SetupError('Rows must be physical row numbers >= 2.')
    worksheet = worksheet if worksheet is not None else connect(settings, config)
    state = snapshot(worksheet, spec)
    numbers = sorted(set(rows)) if rows is not None else sorted(state.rows)
    if any(n not in state.rows for n in numbers):
        raise SetupError('A selected physical row is outside the returned worksheet data.')
    if not dry_run:
        preflight_destination(config)
    result = BatchResult(document_key, dry_run)
    notify = progress or (lambda event: None)
    for number in numbers:
        original = state.rows[number]
        outcome = RowOutcome(number, 'skipped')
        claimed = False
        status = clean(original[state.operations['processing_status']]).upper()
        submission = any(clean(v) for i, v in enumerate(original) if i not in state.operations.values())
        if not submission or status not in ('', 'ERROR'):
            outcome.message = 'Empty non-submission row or ineligible status.'
        else:
            try:
                if not dry_run and not unchanged(worksheet, state, number, original):
                    outcome.outcome = 'changed'
                    outcome.message = 'Row or headers changed since read; no writes performed.'
                else:
                    if not dry_run:
                        try:
                            update_operations(worksheet, state, number, {'processing_status': 'PROCESSING', 'error_message': ''})
                            claimed = True
                        except Exception:
                            # The remote write may have succeeded. Never generate on an uncertain claim.
                            outcome.outcome = 'sync_failed'
                            outcome.synchronization_errors.append('PROCESSING write uncertain; inspect row before retrying.')
                    if outcome.outcome != 'sync_failed' and outcome.outcome != 'changed':
                        values = validate_values(spec, {key: original[index] for key, index in state.fields.items()}, config, settings)
                        data = render_bytes(config.template_path, spec.context_builder(values))
                        filename = output_filename(config, values, number)
                        if dry_run:
                            with TemporaryDirectory(prefix='legal-preview-') as temp:
                                save_atomic(data, Path(temp) / filename)
                            outcome.outcome = 'would_generate'
                        else:
                            outcome.saved_path = save_atomic(data, config.output_dir / filename)
                            try:
                                update_operations(worksheet, state, number, {
                                    'processing_status': 'GENERATED', 'generated_file': filename,
                                    'processed_at': datetime.now().strftime(settings.processed_at_format), 'error_message': ''})
                                outcome.outcome = 'generated'
                            except Exception:
                                outcome.outcome = 'sync_failed'
                                outcome.message = 'Local file saved; completion status not confirmed.'
                                outcome.synchronization_errors.append('GENERATED synchronization failed.')
                                record_error(worksheet, state, number, outcome, settings)
            except Exception as exc:
                outcome.outcome = 'invalid' if dry_run else 'failed'
                outcome.message = str(exc) if isinstance(exc, RowError) else 'Row processing failed; check access/template and retry only after review.'
                if not dry_run and claimed:
                    record_error(worksheet, state, number, outcome, settings)
        result.rows.append(outcome)
        logger.info('%s row=%d outcome=%s', document_key, number, outcome.outcome)
        try:
            notify(outcome)
        except Exception:
            logger.warning('%s row=%d progress callback failed', document_key, number)
    return result


def record_error(worksheet, state, number, outcome, settings):
    try:
        update_operations(worksheet, state, number, {'processing_status': 'ERROR', 'error_message': outcome.message[:settings.error_message_max_length]})
    except Exception:
        outcome.synchronization_errors.append('ERROR synchronization also failed; inspect row manually.')
