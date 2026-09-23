"""Registry-driven Tkinter view and queue-based desktop controller.

The only generation implementation is processor.run_batch. Workers never call Tk,
including after(): polling and all view changes belong to the creating thread.
"""
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from document_registry import SPECS
from models import SetupError
from processor import run_batch

logger = logging.getLogger('legal_generator')


@dataclass(frozen=True)
class TabMetadata:
    key: str
    label: str
    output_dir: Path


def tab_metadata(settings):
    return [TabMetadata(key, settings.documents[key].label, settings.documents[key].output_dir)
            for key in SPECS if key in settings.documents and settings.documents[key].enabled]


def log_failure(action, exc, key='application'):
    # Cloud exceptions/chains may embed credentials or submitted values. Log only
    # exception types and code locations, never their messages, locals or source.
    frames = traceback.extract_tb(exc.__traceback__)
    locations = ' > '.join(f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in frames)
    causes = []
    seen = set()
    cause = exc.__cause__ or exc.__context__
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        causes.append(type(cause).__name__)
        cause = cause.__cause__ or cause.__context__
    logger.error('%s %s error_type=%s causes=%s locations=%s',
                 key, action, type(exc).__name__, ','.join(causes), locations)
    if isinstance(exc, SetupError):
        # Phase-1 SetupError messages are explicit local diagnostics; underlying
        # cloud/credential exception messages must never be logged.
        logger.error('%s setup diagnostic=%s', key, str(exc))


def open_folder(path):
    directory = Path(path)
    if not directory.is_dir():
        raise OSError('Output folder does not exist.')
    if sys.platform == 'win32':
        os.startfile(str(directory))
    else:
        subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', str(directory)],
                       check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class DocumentTab(ttk.Frame):
    def __init__(self, parent, metadata, on_generate, on_browse, on_open):
        super().__init__(parent, padding=20)
        self.key = metadata.key
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=metadata.label, font=('TkDefaultFont', 15, 'bold')).grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 20))
        ttk.Label(self, text='Save Folder').grid(row=1, column=0, sticky='w', pady=(0, 6))
        self.folder = tk.StringVar(master=self, value=str(metadata.output_dir))
        ttk.Entry(self, textvariable=self.folder, state='readonly').grid(
            row=2, column=0, sticky='ew', padx=(0, 10))
        self.browse_button = ttk.Button(self, text='Browse…', command=lambda: on_browse(self.key))
        self.browse_button.grid(row=2, column=1, sticky='e')
        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, columnspan=2, sticky='w', pady=(20, 18))
        self.generate_button = ttk.Button(actions, text='Generate Documents',
                                          command=lambda: on_generate(self.key))
        self.generate_button.grid(row=0, column=0, padx=(0, 10))
        ttk.Button(actions, text='Open Generated Folder', command=lambda: on_open(self.key)).grid(
            row=0, column=1)
        self.status = tk.StringVar(master=self, value='Ready')
        ttk.Label(self, textvariable=self.status, wraplength=540).grid(
            row=4, column=0, columnspan=2, sticky='w', pady=(0, 16))
        counters = ttk.Frame(self)
        counters.grid(row=5, column=0, columnspan=2, sticky='w')
        self.counts = {}
        for column, name in enumerate(('Generated', 'Skipped', 'Failed')):
            variable = tk.StringVar(master=self, value=f'{name}: 0')
            self.counts[name.lower()] = variable
            ttk.Label(counters, textvariable=variable).grid(row=0, column=column, padx=(0, 24))

    def set_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        self.generate_button.configure(state=state)
        self.browse_button.configure(state=state)

    def set_folder(self, path):
        self.folder.set(str(path))

    def set_status(self, text):
        self.status.set(text)

    def set_counts(self, counts):
        for name, variable in self.counts.items():
            variable.set(f'{name.title()}: {counts.get(name, 0)}')


def build_tabs(notebook, settings, on_generate, on_browse, on_open, tab_factory=DocumentTab):
    tabs = {}
    for metadata in tab_metadata(settings):
        tab = tab_factory(notebook, metadata, on_generate, on_browse, on_open)
        notebook.add(tab, text=metadata.label)
        tabs[metadata.key] = tab
    return tabs


class DesktopController:
    def __init__(self, root, store, settings, tabs, processor=run_batch,
                 choose_folder=filedialog.askdirectory, opener=open_folder):
        self.root, self.store, self.settings, self.tabs = root, store, settings, tabs
        self.processor, self.choose_folder, self.opener = processor, choose_folder, opener
        self.events = Queue()
        self.active_key = None
        self.worker = None
        self.owner = threading.get_ident()
        self.closed = False
        self.poll_id = root.after(75, self.poll)

    def _main_thread(self):
        if threading.get_ident() != self.owner:
            raise RuntimeError('Desktop UI operation must run on the main thread.')

    def _controls(self, enabled):
        for tab in self.tabs.values():
            tab.set_enabled(enabled)

    def generate(self, key):
        self._main_thread()
        if self.closed or self.active_key is not None or key not in self.tabs:
            return False
        # Claim before scheduling: double clicks and other tabs cannot start a job.
        self.active_key = key
        self._controls(False)
        self.tabs[key].set_counts({})
        self.tabs[key].set_status('Connecting to Google Sheets…')
        try:
            settings = self.store.load()
            # A configuration edited by an administrator requires a restart so the
            # displayed destination/available tabs cannot disagree with the batch.
            if settings != self.settings:
                raise SetupError('Configuration changed; restart the application.')
            self.worker = threading.Thread(target=self._run, args=(settings, key),
                                           name=f'generate-{key}', daemon=False)
            self.worker.start()
        except Exception as exc:
            log_failure('start failed', exc, key)
            self._finish(key, None, True)
        return True

    def _run(self, settings, key):
        logger.info('%s generation start output_dir=%s', key, settings.documents[key].output_dir)
        try:
            result = self.processor(settings, key, progress=lambda outcome: self.events.put(('progress', key, None)))
            for row in result.rows:
                if row.message and row.outcome != 'skipped':
                    logger.warning('%s row=%s outcome=%s detail=%s', key, row.row_number, row.outcome, row.message)
                for error in row.synchronization_errors:
                    logger.error('%s row=%s sheet_sync_failure=%s', key, row.row_number, error)
            logger.info('%s generation end summary=%s', key, result.counts)
            self.events.put(('done', key, result))
        except Exception as exc:
            log_failure('generation end failed', exc, key)
            self.events.put(('setup' if isinstance(exc, SetupError) else 'error', key, None))

    def poll(self):
        self._main_thread()
        if self.closed:
            return
        # Bound each drain to preserve responsiveness on very large worksheets.
        for _ in range(100):
            try:
                kind, key, payload = self.events.get_nowait()
            except Empty:
                break
            if key != self.active_key:
                continue
            if kind == 'progress':
                self.tabs[key].set_status('Processing…')
            else:
                self._finish(key, payload, kind == 'setup')
        self.poll_id = self.root.after(75, self.poll)

    def _finish(self, key, result, setup=False):
        self._main_thread()
        tab = self.tabs[key]
        if result is None:
            tab.set_status('Setup error — ask your administrator to check setup and logs, then restart.'
                           if setup else 'Generation failed — ask your administrator to check the logs before retrying.')
        else:
            counts = result.counts
            tab.set_counts({**counts, 'failed': sum(counts[k] for k in ('failed', 'sync_failed', 'changed', 'invalid'))})
            status = 'Generation complete' if result.successful else 'Generation completed with errors — ask your administrator to review the logs.'
            if counts['sync_failed'] or any(row.synchronization_errors for row in result.rows):
                status = 'Generation completed with errors — Sheet updates need review before retrying.'
            tab.set_status(status)
        self.active_key = None
        self._controls(True)

    def browse(self, key):
        self._main_thread()
        if self.active_key is not None or self.closed:
            return
        folder = self.choose_folder(parent=self.root, title='Choose Save Folder',
                                    initialdir=str(self.settings.documents[key].output_dir), mustexist=True)
        if not folder:
            return
        try:
            updated = self.store.save_output(key, folder)
            # Preserve all freshly loaded settings and refresh generic metadata.
            self.settings = updated
            for other, tab in self.tabs.items():
                tab.set_folder(updated.documents[other].output_dir)
            self.tabs[key].set_status('Save folder updated')
        except Exception as exc:
            log_failure('save folder failed', exc, key)
            self.tabs[key].set_status('Could not save folder — choose a separate folder for each document and check access.')

    def open(self, key):
        self._main_thread()
        try:
            self.opener(self.settings.documents[key].output_dir)
        except Exception as exc:
            log_failure('open folder failed', exc, key)
            self.tabs[key].set_status('Could not open folder — check that it exists and is accessible.')

    def close(self):
        self._main_thread()
        if self.active_key is not None:
            messagebox.showinfo('Generation in progress', 'Please wait for generation to finish before closing.', parent=self.root)
            return False
        self.closed = True
        self.root.after_cancel(self.poll_id)
        self.root.destroy()
        return True
