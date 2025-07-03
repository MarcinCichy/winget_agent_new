# agent/task_runner.py

import requests
import json
import logging
import time

class TaskRunner:
    def __init__(self, config, winget_agent):
        self.config = config
        self.winget_agent = winget_agent
        self.logger = logging.getLogger("WingetAgent.TaskRunner")

    def fetch_tasks(self, hostname):
        """Pobierz listę zadań dla tego hosta z wszystkich endpointów"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.config.api_key
        }
        all_tasks = []
        for endpoint in self.config.api_endpoints:
            # Załóżmy, że endpoint raportów wygląda tak: http://host:5000/api/report
            # więc endpoint zadań: http://host:5000/api/tasks/NAZWA_HOSTA
            base_url = endpoint.replace("/api/report", "")
            tasks_url = f"{base_url}/api/tasks/{hostname}"
            try:
                resp = requests.get(tasks_url, headers=headers, timeout=15)
                resp.raise_for_status()
                tasks = resp.json()
                if tasks:
                    self.logger.info(f"Pobrano zadania z {tasks_url}: {tasks}")
                    all_tasks.extend([(base_url, t) for t in tasks])
            except Exception as e:
                self.logger.error(f"Błąd pobierania zadań z {tasks_url}: {e}")
        return all_tasks

    def send_task_result(self, base_url, task_id, status):
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.config.api_key
        }
        data = {"task_id": task_id, "status": status}
        try:
            r = requests.post(f"{base_url}/api/tasks/result", json=data, headers=headers, timeout=10)
            r.raise_for_status()
            self.logger.info(f"Zgłoszono wynik zadania {task_id} ({status}) do {base_url}")
        except Exception as e:
            self.logger.error(f"Nie udało się zgłosić wyniku zadania {task_id} do {base_url}: {e}")

    def process_tasks(self, hostname):
        """Obsłuż wszystkie zadania dla danego hosta"""
        tasks = self.fetch_tasks(hostname)
        for base_url, task in tasks:
            command = task.get('command')
            payload = task.get('payload')
            task_id = task.get('id')
            status_final = 'błąd'
            self.logger.info(f"Przetwarzam zadanie {task_id}: {command} (payload={payload})")
            try:
                if command == 'update_package':
                    if self.winget_agent.update_package(payload):
                        status_final = 'zakończone'
                elif command == 'uninstall_package':
                    if self.winget_agent.uninstall_package(payload):
                        status_final = 'zakończone'
                elif command == 'force_report':
                    self.winget_agent.collect_and_report()
                    status_final = 'zakończone'
                else:
                    self.logger.warning(f"Nieznane polecenie zadania: {command}")
            except Exception as e:
                self.logger.error(f"Błąd podczas przetwarzania zadania {task_id}: {e}")
            self.send_task_result(base_url, task_id, status_final)
