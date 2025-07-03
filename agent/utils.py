import os
import subprocess
import logging

def run_powershell(command: str) -> str | None:
    """
    Uruchamia polecenie PowerShell i zwraca wyjście jako string (UTF-8).
    W przypadku błędu loguje wyjątek i zwraca None.
    """
    try:
        full_command = (
            "[System.Threading.Thread]::CurrentThread.CurrentUICulture = [System.Globalization.CultureInfo]::GetCultureInfo('en-US'); "
            "[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "$OutputEncoding = [System.Text.Encoding]::UTF8; " + command
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", full_command],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error("Błąd podczas wykonywania PowerShell: %s", e.stderr)
        return None
    except FileNotFoundError:
        logging.error("Nie znaleziono powershell.exe")
        return None

def find_winget_path(explicit_path: str | None = None) -> str | None:
    """
    Wyszukuje lokalizację winget.exe. Najpierw explicit_path, potem PATH, potem WindowsApps.
    """
    if explicit_path and os.path.isfile(explicit_path):
        return explicit_path
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path_dir, "winget.exe")
        if os.path.isfile(candidate):
            return candidate
    # Dodatkowy fallback – katalog WindowsApps (per user)
    user_root = os.path.expandvars(r"C:\Users")
    if os.path.isdir(user_root):
        for username in os.listdir(user_root):
            winapps = os.path.join(user_root, username, "AppData", "Local", "Microsoft", "WindowsApps", "winget.exe")
            if os.path.isfile(winapps):
                return winapps
    # Ostateczna próba: "where winget"
    try:
        result = subprocess.run(["where", "winget"], capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if os.path.isfile(line.strip()):
                    return line.strip()
    except Exception:
        pass
    return None

# (opcjonalnie możesz tu dodać kolejne narzędzia, np. parsowanie wyników z winget)

def parse_winget_list_output(output: str, blacklist: list[str]) -> list[dict]:
    """
    Parsuje wynik 'winget list' (txt) do listy aplikacji, z filtracją przez blacklist.
    """
    apps = []
    lines = output.strip().splitlines()
    if not lines:
        return apps

    header_line = next((line for line in lines if "Name" in line and "Id" in line and "Version" in line), "")
    if not header_line:
        return apps

    pos_id = header_line.find("Id")
    pos_version = header_line.find("Version")
    pos_available = header_line.find("Available")
    pos_source = header_line.find("Source")
    if pos_available == -1:
        pos_available = pos_source if pos_source != -1 else len(header_line) + 20

    for line in lines:
        if line.strip().startswith("---") or not line.strip() or line == header_line or len(line) < pos_version:
            continue
        try:
            name = line[:pos_id].strip()
            id_ = line[pos_id:pos_version].strip()
            version = line[pos_version:pos_available].strip()
            if not name or name.lower() == "name":
                continue
            name_lower = name.lower()
            if any(k in name_lower for k in blacklist):
                continue
            apps.append({"name": name, "id": id_, "version": version})
        except Exception as e:
            logging.warning("Nie udało się sparsować linii aplikacji: %s | Błąd: %s", line, e)
    return apps

# Podobne funkcje można dodać dla parsowania winget upgrade/output itd.
