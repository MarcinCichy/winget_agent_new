from .config import AgentConfig
from .winget_agent import WingetAgent
from .task_runner import TaskRunner
import time
import sys

def main_loop():
    config = AgentConfig.load_from_env()  # lub .load_from_file()
    winget_agent = WingetAgent(config)
    task_runner = TaskRunner(config, winget_agent)

    winget_agent.logger.info("Agent uruchomiony. Start głównej pętli.")
    report_counter = 0

    while True:
        try:
            # 1. Pobierz hostname (możesz zrobić np. config.hostname)
            hostname = winget_agent.get_hostname()
            # 2. Przetwarzaj zadania z serwera
            task_runner.process_tasks(hostname)
            # 3. Co N cykli generuj raport
            report_counter += 1
            if report_counter >= config.full_report_interval_loops:
                winget_agent.collect_and_report()
                report_counter = 0
            time.sleep(config.loop_interval_seconds)
        except Exception as e:
            winget_agent.logger.error(f"Błąd w głównej pętli: {e}", exc_info=True)
            time.sleep(10)

if __name__ == "__main__":
    if '--install' in sys.argv:
        from .windows_service import install_service
        install_service()
    elif '--remove' in sys.argv:
        from .windows_service import remove_service
        remove_service()
    elif '--runservice' in sys.argv:
        from .windows_service import run_service
        run_service()
    else:
        main_loop()
