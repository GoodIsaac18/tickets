Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Usuary\Downloads\tickets-main\tickets-main"
WshShell.Run """C:\Users\Usuary\Downloads\tickets-main\tickets-main\python_embed\python.exe"" ""C:\Users\Usuary\Downloads\tickets-main\tickets-main\app_emisora.py""", 0, False
