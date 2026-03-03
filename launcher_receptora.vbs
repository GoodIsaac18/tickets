Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\PROTECNICA\Desktop\tickets\tickets\tickets"
WshShell.Run """C:\Users\PROTECNICA\Desktop\tickets\tickets\tickets\python_embed\python.exe"" ""C:\Users\PROTECNICA\Desktop\tickets\tickets\tickets\app_receptora.py""", 0, False
