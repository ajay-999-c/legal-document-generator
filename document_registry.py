"""Explicit registry: adding a document does not change the processor or CLI."""
from documents.noc import SPEC as NOC
from documents.affidavit import SPEC as AFFIDAVIT
from documents.consent import SPEC as CONSENT
from documents.registration import SPEC as REGISTRATION
from documents.by_law import SPEC as BY_LAW
from documents.form_a_registration import SPEC as FORM_A_REGISTRATION
from models import SetupError

SPECS = {spec.key: spec for spec in (NOC, AFFIDAVIT, CONSENT, REGISTRATION, BY_LAW, FORM_A_REGISTRATION)}


def selected(settings, key):
    if key not in SPECS or key not in settings.documents:
        raise SetupError('Unknown or unconfigured document key.')
    config = settings.documents[key]
    if not config.enabled:
        raise SetupError(f'{key}: document is disabled.')
    return SPECS[key], config
