// Czekaj, aż cała strona się załaduje, zanim podepniesz skrypty
document.addEventListener('DOMContentLoaded', () => {

    // --- FUNKCJE POMOCNICZE ---

    // Funkcja do wymuszonego przeładowania strony, omijająca cache
    function forceReload() {
        const url = new URL(window.location);
        url.searchParams.set('t', new Date().getTime());
        window.location.href = url.toString();
    }

    // Nowa, uniwersalna funkcja do odpytywania serwera o status zadania
    const pollTaskStatus = (taskId, onUpdate, onComplete, onError) => {
        const interval = setInterval(() => {
            fetch(`/api/task_status/${taskId}`)
                .then(response => {
                    if (!response.ok) throw new Error('Błąd serwera przy sprawdzaniu statusu.');
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'zakończone' || data.status === 'błąd') {
                        clearInterval(interval);
                        if (onComplete) onComplete(data.status);
                    } else {
                        if (onUpdate) onUpdate(data.status);
                    }
                })
                .catch(err => {
                    clearInterval(interval);
                    if (onError) onError(err);
                });
        }, 5000); // Pytaj co 5 sekund
    };

    // --- LOGIKA ELEMENTÓW ---

    // Logika dla przełącznika motywu
    const toggleButton = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;
    if (toggleButton) {
        toggleButton.addEventListener('click', () => {
            htmlEl.classList.toggle('dark-mode');
            localStorage.setItem('theme', htmlEl.classList.contains('dark-mode') ? 'dark' : 'light');
        });
    }

    // ZMODYFIKOWANA LOGIKA DLA PRZYCISKU ODŚWIEŻ (działa na obu stronach)
    document.querySelectorAll('.refresh-btn').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const originalText = this.textContent;

            const statusCell = this.closest('tr')?.cells[3];
            const notificationBar = document.getElementById('notification-bar');

            const updateStatusText = (text) => {
                if (statusCell) statusCell.textContent = text;
                if (notificationBar) {
                    notificationBar.textContent = text;
                    notificationBar.style.backgroundColor = '#007bff';
                    notificationBar.style.display = 'block';
                }
            };

            this.textContent = 'Wysyłanie...';
            this.disabled = true;

            fetch(`/api/computer/${computerId}/refresh`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' && data.task_id) {
                        updateStatusText('Zlecono. Oczekuję na agenta...');
                        pollTaskStatus(
                            data.task_id,
                            (status) => updateStatusText(`W toku... (Status: ${status})`),
                            (status) => forceReload(),
                            (error) => {
                                updateStatusText('Błąd odpytywania!');
                                this.textContent = originalText;
                                this.disabled = false;
                            }
                        );
                    } else {
                        throw new Error('Nie udało się zlecić zadania.');
                    }
                }).catch(error => {
                    console.error("Błąd sieci:", error);
                    updateStatusText('Błąd zlecenia!');
                    this.textContent = originalText;
                    this.disabled = false;
                });
        });
    });

    /// ZMODYFIKOWANA LOGIKA DLA PRZYCISKU "AKTUALIZUJ"
    document.querySelectorAll('.update-btn:not(.uninstall-btn)').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const updateId = this.dataset.updateId;
            const packageId = this.dataset.packageId;
            const appName = this.closest('tr').cells[1].textContent;
            const statusCell = this.closest('tr').cells[2];
            const originalText = this.textContent;

            if (!confirm(`Czy na pewno chcesz zlecić aktualizację aplikacji "${appName}"?`)) return;

            this.textContent = 'Zlecanie...';
            this.disabled = true;

            fetch(`/api/computer/${computerId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ package_id: packageId, update_id: updateId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.task_id) {
                    if (statusCell) statusCell.innerHTML = '<span class="status-pending">Oczekuje...</span>';
                    // Rozpocznij odpytywanie o status zadania aktualizacji
                    pollTaskStatus(
                        data.task_id,
                        (status) => { if (statusCell) statusCell.innerHTML = `<span class="status-pending">W toku... (${status})</span>`; },
                        (status) => forceReload(),
                        (error) => {
                            if (statusCell) statusCell.innerHTML = '<span class="status-fail">Błąd</span>';
                            this.textContent = originalText;
                            this.disabled = false;
                        }
                    );
                } else {
                    throw new Error('Nie udało się zlecić zadania aktualizacji.');
                }
            })
            .catch(error => {
                console.error("Błąd sieci:", error);
                if (statusCell) statusCell.innerHTML = '<span class="status-fail">Błąd sieci</span>';
                this.textContent = originalText;
                this.disabled = false;
            });
        });
    });

    // ZMODYFIKOWANA LOGIKA DLA PRZYCISKU "ODINSTALUJ"
    document.querySelectorAll('.uninstall-btn').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const packageId = this.dataset.packageId;
            const appName = this.closest('tr').cells[0].textContent;
            const notificationBar = document.getElementById('notification-bar');
            const originalText = this.textContent;

            if (!confirm(`Czy na pewno chcesz zlecić deinstalację aplikacji "${appName}"?\n\nUWAGA: Ta akcja jest nieodwracalna!`)) return;

            this.textContent = 'Zlecanie...';
            this.disabled = true;

            fetch(`/api/computer/${computerId}/uninstall`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ package_id: packageId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.task_id) {
                    notificationBar.textContent = `Zlecono deinstalację dla "${appName}". Oczekuję na agenta...`;
                    notificationBar.style.backgroundColor = '#ffc107';
                    notificationBar.style.display = 'block';
                    // Rozpocznij odpytywanie o status zadania deinstalacji
                    pollTaskStatus(
                        data.task_id,
                        (status) => { notificationBar.textContent = `Deinstalacja w toku... (Status: ${status})`; },
                        (status) => forceReload(),
                        (error) => {
                            notificationBar.textContent = 'Błąd odpytywania!';
                            notificationBar.style.backgroundColor = '#dc3545';
                            this.textContent = originalText;
                            this.disabled = false;
                        }
                    );
                } else {
                    throw new Error('Nie udało się zlecić zadania deinstalacji.');
                }
            })
            .catch(error => {
                console.error("Błąd sieci:", error);
                notificationBar.textContent = `Wystąpił błąd podczas zlecania deinstalacji: ${error.message}`;
                notificationBar.style.backgroundColor = '#dc3545';
                notificationBar.style.display = 'block';
                this.textContent = originalText;
                this.disabled = false;
            });
        });
    });

    // ZMODYFIKOWANA LOGIKA DLA CZARNEJ LISTY
    const blacklistForm = document.getElementById('blacklist-form');
    if (blacklistForm) {
        blacklistForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const computerId = document.querySelector('.refresh-btn').dataset.computerId;
            const keywords = document.getElementById('blacklist-keywords').value;
            const button = this.querySelector('button[type="submit"]');
            const notificationBar = document.getElementById('notification-bar');

            const originalButtonText = button.textContent;

            button.textContent = 'Zapisywanie...';
            button.disabled = true;

            fetch(`/api/computer/${computerId}/blacklist`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ blacklist_keywords: keywords })
            })
            .then(response => {
                if (!response.ok) throw new Error('Błąd zapisu czarnej listy');
                return fetch(`/api/computer/${computerId}/refresh`, { method: 'POST' });
            })
            .then(response => {
                if (!response.ok) throw new Error('Błąd zlecania odświeżenia');
                return response.json();
            })
            .then(refreshData => {
                if (refreshData.task_id) {
                    notificationBar.style.backgroundColor = '#28a745';
                    notificationBar.style.display = 'block';
                    pollTaskStatus(
                        refreshData.task_id,
                        (status) => { notificationBar.textContent = `Zapisano! Oczekuję na zakończenie raportu... (Status: ${status})`; },
                        (status) => forceReload(),
                        (error) => {
                            notificationBar.textContent = 'Błąd odpytywania!';
                            notificationBar.style.backgroundColor = '#dc3545';
                            button.textContent = originalButtonText;
                            button.disabled = false;
                        }
                    );
                } else {
                    throw new Error('Nie otrzymano ID zadania po zleceniu odświeżenia.');
                }
            })
            .catch(error => {
                console.error("Błąd:", error);
                notificationBar.textContent = 'Wystąpił błąd. Sprawdź konsolę.';
                notificationBar.style.backgroundColor = '#dc3545';
                notificationBar.style.display = 'block';
                button.textContent = originalButtonText;
                button.disabled = false;
            });
        });
    }

    // Logika dla przycisku "Odśwież wszystkie"
    const refreshAllBtn = document.getElementById('refresh-all-btn');
    if (refreshAllBtn) {
        refreshAllBtn.addEventListener('click', function() {
            if (!confirm('Czy na pewno chcesz zlecić odświeżenie dla WSZYSTKICH komputerów?')) return;

            const originalText = this.textContent;
            this.textContent = 'Wysyłanie...';
            this.disabled = true;

            fetch('/api/computers/refresh_all', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert(`${data.message}\nStrona przeładuje się automatycznie za około 45 sekund, aby dać agentom czas na odpowiedź.`);
                        setTimeout(forceReload, 45000);
                    } else {
                        alert('Wystąpił błąd podczas zlecania zadań.');
                        this.textContent = originalText;
                        this.disabled = false;
                    }
                })
                .catch(error => {
                    console.error("Błąd sieci:", error);
                    alert('Błąd sieci. Sprawdź konsolę.');
                    this.textContent = originalText;
                    this.disabled = false;
                });
        });
    }
});