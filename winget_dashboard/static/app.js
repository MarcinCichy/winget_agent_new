document.addEventListener('DOMContentLoaded', () => {

    // --- NOWA FUNKCJA DO ZARZĄDZANIA UKŁADEM ---
    const adjustLayout = () => {
        const header = document.querySelector('.header-container');
        const footer = document.querySelector('.main-footer');
        const body = document.body;

        if (header) {
            // Pobierz wysokość nagłówka i dodaj 1.5rem (24px) marginesu
            const headerHeight = header.offsetHeight;
            body.style.paddingTop = `${headerHeight + 24}px`;
        }
        if (footer) {
            // Pobierz wysokość stopki i dodaj 1rem (16px) marginesu
            const footerHeight = footer.offsetHeight;
            body.style.paddingBottom = `${footerHeight + 16}px`;
        }
    };

    // Uruchom funkcję po załadowaniu strony i przy każdej zmianie rozmiaru okna
    adjustLayout();
    window.addEventListener('resize', adjustLayout);


    // --- FUNKCJE POMOCNICZE ---
    function forceReload() {
        const url = new URL(window.location);
        url.searchParams.set('t', new Date().getTime());
        window.location.href = url.toString();
    }

    const pollTaskStatus = (taskId, onUpdate, onComplete, onError) => {
        let attempts = 0;
        const maxAttempts = 36; // 3 minuty max (36 * 5s)
        const interval = setInterval(() => {
            attempts++;
            if (attempts > maxAttempts) {
                clearInterval(interval);
                if (onError) onError(new Error("Zadanie przekroczyło limit czasu."));
                return;
            }

            fetch(`/api/task_status/${taskId}`)
                .then(response => {
                    if (!response.ok) throw new Error('Błąd serwera przy sprawdzaniu statusu.');
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'zakończone' || data.status === 'błąd' || data.status === 'not_found') {
                        clearInterval(interval);
                        if (onComplete) onComplete(data.status);
                    } else {
                        if (onUpdate) onUpdate(data.status);
                    }
                })
                .catch(err => {
                    clearInterval(interval);
                    console.error("Błąd odpytywania o status zadania:", err); // <-- DODAJ TĘ LINIĘ
                    if (onError) onError(err);
                });
        }, 5000); // Pytaj co 5 sekund
    };

    // --- LOGIKA ELEMENTÓW ---

    const toggleButton = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;
    if (toggleButton) {
        toggleButton.addEventListener('click', () => {
            htmlEl.classList.toggle('dark-mode');
            localStorage.setItem('theme', htmlEl.classList.contains('dark-mode') ? 'dark' : 'light');
        });
    }

    document.querySelectorAll('.refresh-btn').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const originalText = this.textContent;

            const statusCell = this.closest('tr')?.cells[3];
            const notificationBar = document.getElementById('notification-bar');

            const updateStatusText = (text) => {
                const capitalizedText = text.charAt(0).toUpperCase() + text.slice(1);
                if (statusCell) statusCell.innerHTML = `<span class="status-pending">${capitalizedText}</span>`;
                if (notificationBar) {
                    notificationBar.textContent = capitalizedText;
                    notificationBar.style.backgroundColor = '#007bff';
                    notificationBar.style.display = 'block';
                }
            };

            const revertButton = () => {
                this.textContent = originalText;
                this.disabled = false;
            };

            this.textContent = 'Wysyłanie...';
            this.disabled = true;

            fetch(`/api/computer/${computerId}/refresh`, { method: 'POST' })
                .then(response => {
                    if (!response.ok) throw new Error('Błąd zlecenia zadania.');
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success' && data.task_id) {
                        updateStatusText('Zlecono');
                        pollTaskStatus(
                            data.task_id,
                            (status) => updateStatusText(`W toku (${status})`),
                            (status) => forceReload(),
                            (error) => {
                                updateStatusText('Błąd odpytywania!');
                                revertButton();
                            }
                        );
                    } else {
                        throw new Error('Nie udało się zlecić zadania.');
                    }
                }).catch(error => {
                    console.error("Błąd:", error);
                    updateStatusText('Błąd zlecenia!');
                    revertButton();
                });
        });
    });

    document.querySelectorAll('.update-btn:not(.uninstall-btn)').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const packageId = this.dataset.packageId;
            const appName = this.closest('tr').cells[1].textContent;

            if (!confirm(`Czy na pewno chcesz zlecić aktualizację aplikacji "${appName}"?`)) return;

            this.disabled = true;
            this.textContent = 'Zlecanie...';

            fetch(`/api/computer/${computerId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ package_id: packageId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success' || !data.task_id) {
                    throw new Error('Nie udało się zlecić zadania aktualizacji.');
                }
                forceReload();
            })
            .catch(error => {
                console.error("Błąd sieci:", error);
                this.textContent = "Błąd";
                alert("Wystąpił błąd: " + error.message);
            });
        });
    });

    document.querySelectorAll('.uninstall-btn').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const packageId = this.dataset.packageId;
            const appName = this.closest('tr').cells[0].textContent;

            if (!confirm(`Czy na pewno chcesz zlecić deinstalację aplikacji "${appName}"?\n\nUWAGA: Ta akcja jest nieodwracalna!`)) return;

            this.disabled = true;
            this.textContent = 'Zlecanie...';

            fetch(`/api/computer/${computerId}/uninstall`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ package_id: packageId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success' || !data.task_id) {
                    throw new Error('Nie udało się zlecić zadania deinstalacji.');
                }
                forceReload();
            })
            .catch(error => {
                console.error("Błąd sieci:", error);
                this.textContent = "Błąd";
                alert("Wystąpił błąd: " + error.message);
            });
        });
    });

    const blacklistForm = document.getElementById('blacklist-form');
    if (blacklistForm) {
        blacklistForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const computerId = document.querySelector('.refresh-btn').dataset.computerId;
            const keywords = document.getElementById('blacklist-keywords').value;
            const button = this.querySelector('button[type="submit"]');
            const notificationBar = document.getElementById('notification-bar');
            const originalButtonText = button.textContent;

            const revertButton = () => {
                button.textContent = originalButtonText;
                button.disabled = false;
            };

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
            .then(response => response.json())
            .then(refreshData => {
                if (refreshData.task_id) {
                    notificationBar.style.backgroundColor = '#28a745';
                    notificationBar.style.display = 'block';
                    pollTaskStatus(
                        refreshData.task_id,
                        (status) => { notificationBar.textContent = `Zapisano! Oczekuję na raport... (Status: ${status})`; },
                        (status) => forceReload(),
                        (error) => {
                            notificationBar.textContent = 'Błąd odpytywania!';
                            notificationBar.style.backgroundColor = '#dc3545';
                            revertButton();
                        }
                    );
                } else { throw new Error('Nie otrzymano ID zadania po zleceniu odświeżenia.'); }
            })
            .catch(error => {
                console.error("Błąd:", error);
                notificationBar.textContent = 'Wystąpił błąd. Sprawdź konsolę.';
                notificationBar.style.backgroundColor = '#dc3545';
                revertButton();
            });
        });
    }

    const refreshAllBtn = document.getElementById('refresh-all-btn');
    if (refreshAllBtn) {
        refreshAllBtn.addEventListener('click', function() {
            if (!confirm('Czy na pewno chcesz zlecić odświeżenie dla WSZYSTKICH komputerów?')) return;
            this.textContent = 'Wysyłanie...';
            this.disabled = true;
            fetch('/api/computers/refresh_all', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert(`${data.message}\nStrona przeładuje się automatycznie za około minuty, aby dać agentom czas na odpowiedź.`);
                        setTimeout(forceReload, 60000);
                    } else {
                        alert('Wystąpił błąd podczas zlecania zadań.');
                        this.textContent = "Odśwież wszystkie";
                        this.disabled = false;
                    }
                })
                .catch(error => {
                    console.error("Błąd sieci:", error);
                    alert('Błąd sieci. Sprawdź konsolę.');
                    this.textContent = "Odśwież wszystkie";
                    this.disabled = false;
                });
        });
    }
});