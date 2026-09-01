Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""C:\Users\User\.adforge\daily_analyst\scheduler_wrapper.ps1""", 0, False
