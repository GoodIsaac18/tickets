
import os
from pathlib import Path

content_emisora = '''Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = currentDir
WshShell.Run """" & currentDir & "\python_embed\python.exe"" """ & currentDir & "\app_emisora.py""", 0, False
'''
with open('launcher_emisora.vbs', 'w', encoding='utf-8') as f: f.write(content_emisora)

content_receptora = content_emisora.replace('app_emisora.py', 'app_receptora.py')
with open('launcher_receptora.vbs', 'w', encoding='utf-8') as f: f.write(content_receptora)

with open('ejecutar_emisora_oculto.vbs', 'w', encoding='utf-8') as f: f.write(content_emisora)
with open('ejecutar_receptora_oculto.vbs', 'w', encoding='utf-8') as f: f.write(content_receptora)

