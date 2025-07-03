# agent/winget_agent.py

import os
import socket
import subprocess
import requests
import json
import logging
from .utils import setup_logger

class WingetAgent:
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger()
        self.winget_path = self.find_winget_path()
        self.blacklist_keywords = config.blacklist_keywords

    def find_winget_path(self):
        # Automatyczne wyszukiwanie ścieżki do winget.exe
        if self.config.winget_path and os.path.isfile(self.config.winget_path):
            return self.config.winget_path
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(path_dir, "winget.exe")
            if os.path.isfile(candidate):
                return candidate
        return None

    def get_active_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            self.logger.error(f"Błąd pobierania IP: {e}")
            return "127.0.0.1"

    def run_command(self, command):
        try:
            full_command = (
                "[System.Threading.Thread]::CurrentThread.CurrentUICulture = [System.Globalization.CultureInfo]::GetCultureInfo('en-US'); "
                "[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                "$OutputEncoding = [System.Text.Encoding]::UTF8; "
                + command
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", full_command],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Błąd polecenia '{command}': {e.stderr}")
            return None
        except FileNotFoundError:
            self.logger.error("Nie znaleziono powershell.exe")
            return None

    def get_system_info(self):
        return {
            "hostname": socket.gethostname(),
            "ip_address": self.get_active_ip()
        }

    def get_reboot_status(self):
        command = "(New-Object -ComObject Microsoft.Update.SystemInfo).RebootRequired"
        output = self.run_command(command)
        return "true" in output.lower() if output else False

    def get_installed_apps(self):
        if not self.winget_path or not os.path.exists(self.winget_path):
            self.logger.error(f"Nie znaleziono winget.exe w {self.winget_path}")
            return []
        command = f'& "{self.winget_path}" list --accept-source-agreements'
        output = self.run_command(command)
        if not output:
            return []
        apps, lines = [], output.strip().splitlines()
        header_line = ""
        for line in lines:
            if "Name" in line and "Id" in line and "Version" in line:
                header_line = line
                break
        if not header_line:
            return []
        pos_id = header_line.find("Id")
        pos_version = header_line.find("Version")
        pos_available = header_line.find("Available")
        pos_source = header_line.find("Source")
        if pos_available == -1:
            pos_available = pos_source if pos_source != -1 else len(header_line) + 20
        for line in lines:
            if (
                line.strip().startswith("---")
                or not line.strip()
                or line == header_line
                or len(line) < pos_version
            ):
                continue
            try:
                name = line[:pos_id].strip()
                id_ = line[pos_id:pos_version].strip()
                version = line[pos_version:pos_available].strip()
                if not name or name.lower() == 'name':
                    continue
                name_lower = name.lower()
                if any(k in name_lower for k in self.blacklist_keywords):
                    continue
                apps.append({"name": name, "id": id_, "version": version})
            except Exception as e:
                self.logger.warning(f"Błąd parsowania linii: {line} | {e}")
        return apps

    def get_available_updates(self):
        if not self.winget_path or not os.path.exists(self.winget_path):
            return []
        command = f'& "{self.winget_path}" upgrade --accept-source-agreements'
        output = self.run_command(command)
        if not output:
            return []
        updates, lines = [], output.strip().splitlines()
        header_line = ""
        for line in lines:
            if "Name" in line and "Id" in line and "Version" in line:
                header_line = line
                break
        if not header_line:
            return []
        pos_id = header_line.find("Id")
        pos_version = header_line.find("Version")
        pos_available = header_line.find("Available")
        pos_source = header_line.find("Source")
        for line in lines:
            if (
                line.strip().startswith("---")
                or "upgrades available" in line.lower()
                or line == header_line
                or len(line) < pos_available
            ):
                continue
            try:
                name = line[:pos_id].strip()
                id_ = line[pos_id:pos_version].strip()
                current_version = line[pos_version:pos_available].strip()
                available_version = line[pos_available:pos_source].strip()
                if name and name != 'Name':
                    updates.append({
                        "name": name,
                        "id": id_,
                        "current_version": current_version,
                        "available_version": available_version
                    })
            except Exception as e:
                self.logger.warning(f"Błąd parsowania aktualizacji: {line} | {e}")
        return updates

    def get_windows_updates(self):
        command = '''try { (New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search("IsInstalled=0 and Type='Software' and IsHidden=0 and RebootRequired=0").Updates | ForEach-Object { [PSCustomObject]@{ Title = $_.Title; KB = $_.KBArticleIDs } } | ConvertTo-Json -Depth 3 } catch { return '[]' }'''
        output = self.run_command(command)
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                self.logger.error("Błąd dekodowania JSON z Windows Updates.")
                return []
        return []

    def update_package(self, package_id):
        command = f'& "{self.winget_path}" upgrade --id "{package_id}" --accept-package-agreements --accept-source-agreements --disable-interactivity'
        return self.run_command(command) is not None

    def uninstall_package(self, package_id):
        command = f'& "{self.winget_path}" uninstall --id "{package_id}" --accept-source-agreements --disable-interactivity --silent'
        return self.run_command(command) is not None

    def collect_and_report(self):
        """Zbierz informacje i wyślij do wszystkich endpointów"""
        system_info = self.get_system_info()
        payload = {
            "hostname": system_info["hostname"],
            "ip_address": system_info["ip_address"],
            "reboot_required": self.get_reboot_status(),
            "installed_apps": self.get_installed_apps(),
            "available_app_updates": self.get_available_updates(),
            "pending_os_updates": self.get_windows_updates()
        }
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.config.api_key
        }
        for endpoint in self.config.api_endpoints:
            try:
                r = requests.post(endpoint, json=payload, headers=headers, timeout=30)
                r.raise_for_status()
                self.logger.info(f"Raport wysłany do {endpoint}")
            except Exception as e:
                self.logger.error(f"Błąd wysyłki raportu do {endpoint}: {e}")
