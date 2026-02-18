' Keyence MD-X2000 Communication Script - Silent Startup
' This VBS runs the script without showing a console window using venv

Set WshShell = CreateObject("WScript.Shell")
projectDir = "C:\Users\Worrakirs Boonchan\.gemini\antigravity\scratch\keyence_mdx2000"
WshShell.CurrentDirectory = projectDir

' Run Python script from venv hidden (0 = hidden, False = don't wait)
WshShell.Run """" & projectDir & "\venv\Scripts\pythonw.exe"" """ & projectDir & "\main.py"" --continuous", 0, False

Set WshShell = Nothing

