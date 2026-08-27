Set WshShell = CreateObject("WScript.Shell")
' Launches the CryptoArena tournament completely silently in background
WshShell.Run "python run_tournament.py", 0, False
