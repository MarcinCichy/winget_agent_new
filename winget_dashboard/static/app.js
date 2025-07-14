document.addEventListener('DOMContentLoaded', () => {

    // --- FUNKCJA DO ZARZĄDZANIA UKŁADEM ---
    const adjustLayout = () => {
        const header = document.querySelector('.header-container');
        const footer = document.querySelector('.main-footer');
        const body = document.body;

        if (header) {
            const headerHeight = header.offsetHeight;
            body.style.paddingTop = `${headerHeight + 24}px`;
        }
        if (footer) {
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
                    const finalStatuses = ['zakończone', 'błąd', 'niepowodzenie_interwencja_uzytkownika', 'not_found'];
                    if (finalStatuses.includes(data.status)) {
                        clearInterval(interval);
                        if (onComplete) onComplete(data.status);
                    } else {
                        if (onUpdate) onUpdate(data.status);
                    }
                })
                .catch(err => {
                    clearInterval(interval);
                    console.error("Błąd odpytywania o status zadania:", err);
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

    // --- NOWA, ZUNIFIKOWANA LOGIKA DLA PRZYCISKÓW AKCJI Z MENU ---
    function handleActionButtonClick(e) {
        e.preventDefault();
        const target = e.target.closest('[data-action]');

        const action = target.dataset.action;
        const computerId = target.dataset.computerId;
        const packageId = target.dataset.packageId;
        const force = action === 'force';

        const actionGroup = target.closest('.action-group');
        const isUninstall = actionGroup.querySelector('.uninstall-btn') !== null;

        const appName = target.closest('tr').cells[isUninstall ? 0 : 1].textContent.trim();
        const actionType = isUninstall ? 'deinstalacji' : 'aktualizacji';
        const forceText = force ? 'WYMUSIĆ' : 'poprosić o';

        if (!confirm(`Czy na pewno chcesz ${forceText} ${actionType} aplikacji "${appName}"?`)) {
            return;
        }

        const apiUrl = isUninstall ? `/api/computer/${computerId}/uninstall` : `/api/computer/${computerId}/update`;

        const buttonToDisable = actionGroup.querySelector('.main-action');
        buttonToDisable.textContent = 'Zlecanie...';
        buttonToDisable.disabled = true;

        fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ package_id: packageId, force: force })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'success') throw new Error('Nie udało się zlecić zadania.');
            forceReload();
        })
        .catch(error => {
            console.error("Błąd sieci:", error);
            alert("Wystąpił błąd: " + error.message);
            buttonToDisable.textContent = isUninstall ? 'Odinstaluj' : 'Aktualizuj';
            buttonToDisable.disabled = false;
        });
    }

    document.querySelectorAll('.action-group').forEach(group => {
        const toggleBtn = group.querySelector('.dropdown-toggle');
        const menu = group.querySelector('.dropdown-menu');

        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            // Zamknij inne otwarte menu
            document.querySelectorAll('.dropdown-menu.show').forEach(otherMenu => {
                if (otherMenu !== menu) {
                    otherMenu.classList.remove('show');
                }
            });
            menu.classList.toggle('show');
        });

        group.addEventListener('click', (e) => {
            if (e.target.matches('.main-action, .dropdown-item')) {
                handleActionButtonClick(e);
            }
        });
    });

    // Zamknij menu, jeśli kliknięto gdziekolwiek indziej
    window.addEventListener('click', (e) => {
        if (!e.target.closest('.action-group')) {
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });

    // --- LOGIKA MODALA ---
    const modal = document.getElementById('error-modal');
    if (modal) {
        const closeBtn = modal.querySelector('.close-btn');
        const errorContent = document.getElementById('error-details-content');

        document.querySelectorAll('.details-btn').forEach(button => {
            button.addEventListener('click', function() {
                const taskId = this.dataset.taskId;
                fetch(`/api/task_status/${taskId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data && data.result_details) {
                            errorContent.textContent = data.result_details;
                            modal.style.display = 'block';
                        } else {
                            alert('Brak szczegółów błędu dla tego zadania.');
                        }
                    });
            });
        });

        closeBtn.onclick = () => { modal.style.display = 'none'; };
        window.onclick = (event) => {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        };
    }

    // --- POZOSTAŁE EVENT LISTENERY ---

    document.querySelectorAll('.refresh-btn').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const originalText = this.textContent;
            this.textContent = 'Wysyłanie...';
            this.disabled = true;

            const notificationBar = document.getElementById('notification-bar');

            fetch(`/api/computer/${computerId}/refresh`, { method: 'POST' })
                .then(response => {
                    if (!response.ok) throw new Error('Błąd zlecenia zadania.');
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success' && data.task_id) {
                        if (notificationBar) {
                            notificationBar.textContent = 'Zlecono odświeżenie. Oczekiwanie na raport...';
                            notificationBar.style.backgroundColor = '#007bff';
                            notificationBar.style.display = 'block';
                        }
                        pollTaskStatus(
                            data.task_id,
                            (status) => { if(notificationBar) notificationBar.textContent = `W toku... (Status: ${status})` },
                            (status) => forceReload(),
                            (error) => {
                                if(notificationBar) {
                                    notificationBar.textContent = 'Błąd odpytywania!';
                                    notificationBar.style.backgroundColor = '#dc3545';
                                }
                                this.textContent = originalText;
                                this.disabled = false;
                            }
                        );
                    } else {
                        throw new Error('Nie udało się zlecić zadania.');
                    }
                }).catch(error => {
                    console.error("Błąd:", error);
                    if (notificationBar) {
                        notificationBar.textContent = 'Błąd zlecenia odświeżenia!';
                        notificationBar.style.backgroundColor = '#dc3545';
                        notificationBar.style.display = 'block';
                    }
                    this.textContent = originalText;
                    this.disabled = false;
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
                            button.textContent = 'Zapisz zmiany';
                            button.disabled = false;
                        }
                    );
                } else { throw new Error('Nie otrzymano ID zadania po zleceniu odświeżenia.'); }
            })
            .catch(error => {
                console.error("Błąd:", error);
                notificationBar.textContent = 'Wystąpił błąd. Sprawdź konsolę.';
                notificationBar.style.backgroundColor = '#dc3545';
                button.textContent = 'Zapisz zmiany';
                button.disabled = false;
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
                        alert(`${data.message}\nStrona przeładuje się automatycznie za kilka minut, aby dać agentom czas na odpowiedź.`);
                        setTimeout(forceReload, 180000); // 3 minuty
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