"""Offline extension fixtures; milestone adapters are registered only inside tests."""
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from document_generator import validate_values, render_bytes
from models import DocumentSettings

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = 'खसरा नंबर 343/1, 338/1/2 ग्राम बिसनावदा तहसील राऊ जिला इंदौर (म.प्र.)'


def configured(settings, spec, template, worksheet):
    config = DocumentSettings(spec.key, True, spec.key, worksheet,
                              ROOT / 'templates' / template,
                              settings.config_path.parent / 'generated' / spec.key,
                              spec.key.upper() + '_{association_name}_{row_number}.docx',
                              '%Y-%m-%d')
    return replace(settings, documents={**settings.documents, spec.key: config})


def render(spec, settings, values):
    config = settings.documents[spec.key]
    data = validate_values(spec, values, config, settings)
    context = spec.context_builder(data)
    return context, render_bytes(config.template_path, context)


def assert_style_resources_unchanged(template, output):
    with ZipFile(template) as before, ZipFile(BytesIO(output)) as after:
        for name in before.namelist():
            if name.startswith(('word/styles', 'word/numbering', 'word/theme', 'word/media')):
                a, b = before.read(name), after.read(name)
                assert (ET.canonicalize(a) == ET.canonicalize(b)) if name.endswith('.xml') else (a == b)


def register_for_test(monkeypatch, spec):
    from document_registry import SPECS
    monkeypatch.setitem(SPECS, spec.key, spec)
