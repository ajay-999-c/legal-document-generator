"""Legal Document Generator desktop entry point; startup never contacts Sheets."""
import logging
from logging.handlers import RotatingFileHandler
import tkinter as tk
from tkinter import ttk

from desktop import DesktopController, build_tabs, log_failure
from desktop_config import DesktopConfig
import runtime_paths


def configure_desktop_logging(settings=None):
    path = runtime_paths.desktop_log_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('legal_generator')
    logger.setLevel(settings.log_level if settings else 'INFO')
    logger.propagate = False
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=4, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger, handler


def create_application(root, store=None, startup_error=None):
    root.title('Legal Document Generator')
    root.geometry('700x390')
    root.minsize(620, 360)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    store = store or DesktopConfig()
    try:
        if startup_error is not None:
            raise startup_error
        settings = store.load()
        notebook = ttk.Notebook(root, padding=8)
        notebook.grid(row=0, column=0, sticky='nsew')
        controller = None
        tabs = build_tabs(notebook, settings, lambda key: controller.generate(key),
                          lambda key: controller.browse(key), lambda key: controller.open(key))
        controller = DesktopController(root, store, settings, tabs)
        root.protocol('WM_DELETE_WINDOW', controller.close)
        if not tabs:
            ttk.Label(root, text='No documents enabled. Ask your administrator to check setup.').grid(row=1, column=0, pady=12)
        return controller
    except Exception as exc:
        log_failure('startup setup failed', exc)
        ttk.Label(root, text='Setup error\n\nAsk your administrator to check the configuration and logs,\nthen restart the application.',
                  padding=24, justify='left').grid(row=0, column=0, sticky='nw')
        return None


def main():
    root = tk.Tk()
    store = DesktopConfig()
    handler = logger = None
    startup_error = None
    try:
        # Establish a fallback log before parsing potentially missing/invalid YAML.
        try:
            logger, handler = configure_desktop_logging()
            settings = store.load()
            logger.removeHandler(handler)
            handler.close()
            handler = None
            logger, handler = configure_desktop_logging(settings)
        except Exception as exc:
            startup_error = exc
            log_failure('logging/configuration setup failed', exc)
        def callback_error(kind, value, trace):
            log_failure('UI callback failed', value)
            from tkinter import messagebox
            messagebox.showerror('Application error', 'An operation failed. Ask your administrator to review the logs.', parent=root)
        root.report_callback_exception = callback_error
        create_application(root, store, startup_error)
        root.mainloop()
    finally:
        if handler is not None:
            logger.removeHandler(handler)
            handler.close()


if __name__ == '__main__':
    main()
