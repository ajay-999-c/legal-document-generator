"""Safe command-line entry point. Imports never authenticate or generate files."""
import argparse
import logging
from pathlib import Path
from datetime import datetime
from config_manager import load_settings, DATE_FORMATS
from document_registry import SPECS, selected
from document_generator import clean, preflight_template
from models import SetupError
from processor import run_batch
from sheets_service import connect, snapshot


def row_numbers(text):
    try:
        if not text or any(not part.strip().isascii() or not part.strip().isdecimal() for part in text.split(',')):
            raise ValueError
        numbers = [int(part.strip()) for part in text.split(',')]
        if any(n < 2 for n in numbers):
            raise ValueError
        return sorted(set(numbers))
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use comma-separated physical row numbers >= 2.') from exc


def parser():
    p = argparse.ArgumentParser(description='Selected-document Sheets → DOCX backend. Generate writes unless --dry-run is supplied.')
    p.add_argument('--config', type=Path, help='One runtime YAML file; defaults beside main.py.')
    commands = p.add_subparsers(dest='command', required=True)
    for name in ('list-documents', 'validate-config', 'check-sheets', 'generate'):
        command = commands.add_parser(name)
        command.add_argument('--config', type=Path, default=argparse.SUPPRESS)
        if name in ('check-sheets', 'generate'):
            command.add_argument('--document', required=True, choices=tuple(SPECS))
        if name == 'generate':
            command.add_argument('--rows', type=row_numbers, help='Omit only for a deliberate full eligible batch.')
            command.add_argument('--dry-run', action='store_true', help='No Sheet writes or persistent generated documents.')
    return p


def local_checks(settings):
    ok = True
    print('Credentials: ' + ('file present (contents/authentication not checked)' if settings.credentials_file.is_file() else 'MISSING; provision separately'))
    if not settings.credentials_file.is_file():
        ok = False
    for key, config in settings.documents.items():
        if not config.enabled:
            print(f'{key}: disabled')
            continue
        try:
            preflight_template(SPECS[key], config, settings)
            if config.output_dir.exists() and not config.output_dir.is_dir():
                raise SetupError(f'{key}: output path is not a directory.')
            print(f'{key}: template/schema OK; destination write access checked only at generation')
        except SetupError as exc:
            print(str(exc))
            ok = False
    return 0 if ok else 2


def sheet_checks(settings, key):
    spec, config = selected(settings, key)
    preflight_template(spec, config, settings)
    state = snapshot(connect(settings, config), spec)
    print(f'{key}: headers OK; {len(state.rows)} physical data rows read. Read access only; write access unverified.')
    status_counts = {'eligible': 0, 'skip_status': 0, 'empty': 0}
    submissions = []
    eligible_rows = []
    for number, row in state.rows.items():
        if not any(clean(v) for i, v in enumerate(row) if i not in state.operations.values()):
            status_counts['empty'] += 1
            continue
        submissions.append(row)
        status = clean(row[state.operations['processing_status']]).upper()
        status_counts['eligible' if status in ('', 'ERROR') else 'skip_status'] += 1
        if status in ('', 'ERROR'):
            eligible_rows.append(number)
    print(', '.join(f'{name}={count}' for name, count in status_counts.items()))
    print('Eligible physical row numbers (first 100): ' + ', '.join(map(str, eligible_rows[:100])))
    mismatches = 0
    for field in spec.fields:
        if field.kind != 'date':
            continue
        blank = valid = invalid = 0
        compatible = {fmt: 0 for fmt in sorted(DATE_FORMATS)}
        for row in submissions:
            value = clean(row[state.fields[field.parameter]])
            if not value:
                blank += 1
            else:
                for fmt in compatible:
                    try:
                        datetime.strptime(value, fmt)
                        compatible[fmt] += 1
                    except ValueError:
                        pass
                try:
                    datetime.strptime(value, config.input_date_format)
                    valid += 1
                except ValueError:
                    invalid += 1
        mismatches += invalid
        print(f'{field.parameter}: configured={config.input_date_format}, valid={valid}, blank={blank}, mismatch={invalid}')
        if invalid:
            print('  Compatible format counts (diagnostic only): ' + ', '.join(f'{fmt}={count}' for fmt, count in compatible.items() if count))
    print('No dates were guessed. Ambiguous slash values require operator confirmation of the configured convention.')
    return 1 if mismatches else 0


def configure_logging(settings):
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('legal_generator')
    logger.setLevel(settings.log_level)
    logger.propagate = False
    handler = logging.FileHandler(settings.log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger, handler


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == 'list-documents':
        for key, spec in SPECS.items():
            print(f'{key}: schema {spec.version}, {len(spec.fields)} inputs, {sum(f.required for f in spec.fields)} required (registry only; enabled state is in config.yaml)')
        return 0
    try:
        settings = load_settings(args.config)
        if args.command == 'validate-config':
            return local_checks(settings)
        if args.command == 'check-sheets':
            return sheet_checks(settings, args.document)
        logger, handler = configure_logging(settings)
        try:
            result = run_batch(settings, args.document, args.rows, args.dry_run)
        finally:
            logger.removeHandler(handler)
            handler.close()
        for row in result.rows:
            print(f'row {row.row_number}: {row.outcome}' + (f' — {row.message}' if row.message else ''))
            if row.saved_path:
                print(f'  saved: {row.saved_path}')
            for error in row.synchronization_errors:
                print(f'  {error}')
        print(', '.join(f'{name}={count}' for name, count in result.counts.items()))
        return 0 if result.successful else 1
    except SetupError as exc:
        print(f'Setup error: {exc}')
        return 2
    except Exception:
        # Cloud exceptions can contain URLs, values, or credential material.
        print('Operation failed; check configured access, connectivity and local paths. No sensitive exception details logged.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
