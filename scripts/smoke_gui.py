"""Display-required, offline Tk smoke test. Does not read office config/credentials."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_application
from desktop_config import DesktopConfig
from models import BatchResult, RowOutcome
from tests.conftest import config_data, settings
from tests.test_desktop_six import six_config, KEYS, LABELS


def main():
    with TemporaryDirectory(prefix='legal-gui-smoke-') as temp:
        synthetic = settings.__wrapped__(Path(temp), six_config(config_data.__wrapped__()))
        root = tk.Tk()
        controller = create_application(root, DesktopConfig(synthetic.config_path))
        assert controller is not None
        assert tuple(controller.tabs) == KEYS
        assert tuple(controller.tabs[k].master.tab(controller.tabs[k], "text") for k in KEYS) == LABELS
        assert len({t.folder.get() for t in controller.tabs.values()}) == 6
        calls = []
        def fake_processor(configuration, key, progress):
            calls.append(key)
            progress(RowOutcome(2, 'generated'))
            return BatchResult(key, False, [RowOutcome(2, 'generated')])
        controller.processor = fake_processor
        failures = []
        def report_error(kind, value, tb):
            failures.append(value)
            root.destroy()
        root.report_callback_exception = report_error
        def check():
            root.update_idletasks()
            for tab in controller.tabs.values():
                assert tab.winfo_width() > 1
                assert tab.generate_button.winfo_reqwidth() > 1
                assert str(tab.generate_button.cget('state')) != 'disabled'
            controller.tabs[KEYS[len(calls)]].generate_button.invoke()
            assert all(str(t.generate_button.cget('state')) == 'disabled' for t in controller.tabs.values())
            root.after(200, finish)
        def finish():
            if controller.active_key:
                root.after(100, finish)
                return
            key = calls[-1]
            assert controller.tabs[key].status.get() == 'Generation complete'
            assert controller.tabs[key].counts['generated'].get() == 'Generated: 1'
            for pending in KEYS[len(calls):]:
                assert controller.tabs[pending].status.get() == 'Ready'
            assert all(str(t.generate_button.cget('state')) == 'normal' for t in controller.tabs.values())
            if len(calls) < len(KEYS):
                notebook.select(len(calls))
                root.after(100, check)
            else:
                assert tuple(calls) == KEYS
                controller.close()
        # Display every page before checking geometry of hidden notebook children.
        notebook = controller.tabs['noc'].master
        def show(index=0):
            notebook.select(index)
            if index < len(KEYS) - 1:
                root.after(200, lambda: show(index + 1))
            else:
                root.after(200, check)
        root.after(200, show)
        root.after(20000, lambda: report_error(RuntimeError, RuntimeError('Smoke test timed out'), None))
        root.mainloop()
        if failures:
            raise failures[0]
        print('PASS: real Tk window, six tabs in order, independent folders, layout, six fake workers, controls and main-thread completion; no Sheets access.')


if __name__ == '__main__':
    main()
