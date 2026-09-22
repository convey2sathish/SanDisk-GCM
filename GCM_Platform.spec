# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the GCM Platform 2.0 standalone executable.
# Build:  pyinstaller GCM_Platform.spec --clean -y
# Output: dist\GCM_Platform.exe (one-file, console window shows the local URL and log)
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('countries_data.json', '.'),
    ('surveillance_log.json', '.'),
]
# python-docx needs its default template; anthropic ships type/JSON data
datas += collect_data_files('docx')
try:
    datas += collect_data_files('anthropic')
except Exception:
    pass

hiddenimports = [
    'routes_core', 'routes_alerts', 'routes_docaudit', 'routes_risk',
    'risk_engine', 'alert_explainer', 'ai_bridge', 'expert_advisor',
    'surveillance_data', 'reg_surveillance', 'doc_audit_engine', 'excel_export',
    'compliance_db', 'config', 'store',
    'pypdf', 'docx', 'openpyxl', 'tkinter', 'tkinter.filedialog',
]
try:
    hiddenimports += collect_submodules('anthropic')
except Exception:
    pass

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'IPython', 'notebook', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GCM_Platform',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/img/app.ico' if os.path.exists('static/img/app.ico') else None,
)
