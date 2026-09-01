Set shell = CreateObject("WScript.Shell")
shell.Run "powershell.exe -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & _
    "C:\Users\User\.adforge\bot\bot_scheduler.ps1""", 0, False
