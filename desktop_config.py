"""Desktop persistence over the existing strict Phase-1 configuration loader."""
from dataclasses import replace
from pathlib import Path
from tempfile import NamedTemporaryFile
import os
import yaml

from config_manager import UniqueLoader, load_settings
import runtime_paths
from models import SetupError


class DesktopConfig:
    def __init__(self, path=None):
        self.path = Path(path or runtime_paths.config_path()).expanduser().resolve()
        self.provision_missing = path is None and (runtime_paths.is_windows() or runtime_paths.is_frozen())

    def _provision(self):
        if self.path.exists() or not self.provision_missing:
            return
        seed = (runtime_paths.resource_root() / 'config.example.yaml').read_bytes()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Exclusive creation: never replace an existing office configuration.
            with self.path.open('xb') as stream:
                stream.write(seed)
        except FileExistsError:
            pass

    def load(self):
        self._provision()
        try:
            raw = yaml.load(self.path.read_text(encoding='utf-8'), Loader=UniqueLoader)
        except (OSError, yaml.YAMLError) as exc:
            raise SetupError('Cannot read config.yaml; check path and YAML syntax.') from exc
        # Only absent/blank settings receive defaults; never replace a selected
        # path merely because the directory has not been created yet.
        changed = False
        if isinstance(raw, dict) and isinstance(raw.get('documents'), dict):
            for key, document in raw['documents'].items():
                if isinstance(document, dict) and document.get('output_dir') in (None, ''):
                    label = document.get('label')
                    if isinstance(label, str) and label.strip():
                        document['output_dir'] = str(runtime_paths.default_output(key, label))
                        changed = True
        if changed:
            self._write(raw)
        settings = load_settings(self.path)
        if runtime_paths.is_frozen() or runtime_paths.is_windows():
            documents = {}
            for key, config in settings.documents.items():
                template = Path(raw['documents'][key]['template_path']).expanduser()
                if not template.is_absolute():
                    template = (runtime_paths.resource_root() / template).resolve()
                    if not template.is_relative_to(runtime_paths.resource_root().resolve()):
                        raise SetupError('Bundled template path must stay inside application resources.')
                    config = replace(config, template_path=template)
                documents[key] = config
            settings = replace(settings, documents=documents)
        return settings

    def save_output(self, key, folder):
        """Validate the full candidate before atomically replacing the single YAML.

        Read afresh so unrelated administrator changes are preserved. An unwritable
        destination/config leaves both the previous file and displayed state intact.
        """
        current = self.load()
        if key not in current.documents or not current.documents[key].enabled:
            raise SetupError('Unknown or disabled document.')
        directory = Path(folder).expanduser().resolve()
        if not directory.is_dir():
            raise SetupError('Select an existing folder.')
        data = yaml.load(self.path.read_text(encoding='utf-8'), Loader=UniqueLoader)
        data['documents'][key]['output_dir'] = str(directory)
        self._write(data)
        return self.load()

    def _write(self, data):
        temporary = None
        try:
            with NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                    prefix='.config-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
                stream.flush()
                os.fsync(stream.fileno())
            load_settings(temporary)
            if self.path.exists():
                temporary.chmod(self.path.stat().st_mode & 0o777)
            temporary.replace(self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
