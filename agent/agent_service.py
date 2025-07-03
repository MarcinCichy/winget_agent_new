import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import logging

class WingetAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WingetAgentService"
    _svc_display_name_ = "Winget Agent (Windows update & inventory agent)"
    _svc_description_ = "Agent zbierający i zgłaszający informacje o oprogramowaniu oraz aktualizacjach."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        # Zmień katalog roboczy na folder agenta (ważne dla PyInstaller)
        os.chdir(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(__file__))

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        import main  # <-- to twój agent/main.py, wejście do logiki agenta!
        logging.basicConfig(filename="agent_service.log", level=logging.INFO)
        servicemanager.LogInfoMsg("WingetAgentService uruchomiony.")
        try:
            main.main()
        except Exception as e:
            logging.exception("Błąd w usłudze: %s", e)
        servicemanager.LogInfoMsg("WingetAgentService zatrzymany.")

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(WingetAgentService)
