"""
System utility helpers: opening folders in native OS File Explorer,
and invoking native OS folder picker dialogs.
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def open_folder_in_os(folder_path: str) -> str:
    """
    Opens the directory in the OS file explorer (Windows Explorer, macOS Finder, Linux xdg-open).
    Creates directory if it does not exist yet so the explorer opens cleanly.
    In headless cloud environments (e.g. Google Cloud Run), gracefully resolves path without blocking.
    """
    p = Path(folder_path).resolve()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(p))
            else:
                subprocess.Popen(["explorer", str(p)])
        except Exception:
            try:
                subprocess.Popen(["explorer", str(p)])
            except Exception:
                pass
    elif sys.platform == "darwin":
        try:
            subprocess.Popen(["open", str(p)])
        except Exception:
            pass
    else:
        if os.environ.get("DISPLAY"):
            try:
                subprocess.Popen(["xdg-open", str(p)])
            except Exception:
                pass

    return Path(p).as_posix()


def pick_folder_dialog(initial_dir: Optional[str] = None) -> str:
    """
    Launches a native OS folder picker dialog and returns the selected path as POSIX string.
    Runs in an isolated subprocess to keep FastAPI's async event loop unblocked.
    In headless cloud environments without display or during tests, returns empty string immediately.
    """
    if os.environ.get("CI") or os.environ.get("HEADLESS") or os.environ.get("TESTING") or (sys.platform != "win32" and not os.environ.get("DISPLAY")):
        return ""
    resolved_init = ""
    if initial_dir and initial_dir.strip():
        try:
            init_p = Path(initial_dir.strip()).resolve()
            if init_p.exists():
                resolved_init = str(init_p)
        except Exception:
            pass

    # 1. Try Tkinter in a standalone subprocess
    code_tk = """
import sys
from pathlib import Path
try:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    init_d = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ''
    p = filedialog.askdirectory(title='Select Working Directory for SDD Pod', initialdir=init_d or None)
    root.destroy()
    if p:
        print(Path(p).as_posix())
except Exception:
    pass
"""
    try:
        res = subprocess.run(
            [sys.executable, "-c", code_tk, resolved_init],
            capture_output=True,
            text=True,
            timeout=10
        )
        selected = res.stdout.strip()
        if selected:
            return selected
    except Exception:
        pass

    # 2. On Windows, fallback to PowerShell FolderBrowserDialog
    if sys.platform == "win32":
        ps_code = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Select Working Directory for SDD Pod'
$dialog.ShowNewFolderButton = $true
$init = '{resolved_init.replace("'", "''")}'
if ($init -and (Test-Path $init)) {{ $dialog.SelectedPath = $init }}
$top = New-Object System.Windows.Forms.Form
$top.TopMost = $true
$res = $dialog.ShowDialog($top)
if ($res -eq [System.Windows.Forms.DialogResult]::OK) {{
    Write-Output $dialog.SelectedPath
}}
"""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True,
                text=True,
                timeout=10
            )
            selected = res.stdout.strip()
            if selected:
                return Path(selected).as_posix()
        except Exception:
            pass

    return ""
