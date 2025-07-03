import win32serviceutil
import win32service
import win32event
import servicemanager

from .main import main_loop

SERVICE_NAME = "WingetAgentService"

class WingetAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = "Winget Agent - Zarządzanie oprogramowaniem"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        main_loop()

def install_service():
    win32serviceutil.InstallService(
        __file__,
        SERVICE_NAME,
        "Winget Agent - Zarządzanie oprogramowaniem"
    )
    print("Usługa zainstalowana")

def remove_service():
    win32serviceutil.RemoveService(SERVICE_NAME)
    print("Usługa odinstalowana")

def run_service():
    win32serviceutil.HandleCommandLine(WingetAgentService)
