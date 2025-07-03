# agent_service.spec
# Tworzy EXE gotowe do uruchomienia jako usługa
block_cipher = None

a = Analysis(['agent_service.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='agent_service',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )  # <--- uruchamiaj jako usługa, nie pokazuj okna
