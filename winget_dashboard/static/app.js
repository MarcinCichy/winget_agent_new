document.addEventListener('DOMContentLoaded', () => {

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

    adjustLayout();
    window.addEventListener('resize', adjustLayout);


    function forceReload() {
        const url = new URL(window.location);
        url.searchParams.set('t', new Date().getTime());
        window.location.href = url.toString();
    }

    const pollTaskStatus = (taskId, onUpdate, onComplete, onError) => {
        let attempts = 0;
        const maxAttempts = 36;
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
        }, 5000);
    };

    const toggleButton = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;
    if (toggleButton) {
        toggleButton.addEventListener('click', () => {
            htmlEl.classList.toggle('dark-mode');
            localStorage.setItem('theme', htmlEl.classList.contains('dark-mode') ? 'dark' : 'light');
        });
    }

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

    window.addEventListener('click', (e) => {
        if (!e.target.closest('.action-group')) {
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
        }
    });

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

    // --- NOWY KOD DO OBSŁUGI STRONY USTAWIEŃ ---

    // 1. Informacja zwrotna po wygenerowaniu agenta
    const generateAgentForm = document.getElementById('generate-agent-form');
    if (generateAgentForm) {
        generateAgentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const button = document.getElementById('generate-agent-btn');
            const originalText = button.textContent;
            button.textContent = 'Generowanie...';
            button.disabled = true;

            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Błąd serwera podczas generowania pliku.');
                }
                // Pobierz nazwę pliku z nagłówka, jeśli jest dostępna
                const disposition = response.headers.get('Content-Disposition');
                let filename = 'agent.exe';
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) {
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }
                return response.blob().then(blob => ({ blob, filename }));
            })
            .then(({ blob, filename }) => {
                // Utwórz link i zasymuluj kliknięcie, aby pobrać plik
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();

                // Informacja zwrotna dla użytkownika
                alert('Plik agent.exe został pomyślnie wygenerowany i pobrany!');
            })
            .catch(error => {
                console.error('Błąd generowania agenta:', error);
                alert('Wystąpił błąd podczas generowania agenta. Sprawdź konsolę serwera.');
            })
            .finally(() => {
                button.textContent = originalText;
                button.disabled = false;
            });
        });
    }

    // 2. Obsługa niestandardowego przycisku do wgrywania plików
    const agentFileInput = document.getElementById('agent_file_input');
    const fileChosenLabel = document.getElementById('file-chosen-label');
    if (agentFileInput && fileChosenLabel) {
        agentFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                fileChosenLabel.textContent = this.files[0].name;
                fileChosenLabel.style.opacity = '1';
                fileChosenLabel.style.fontStyle = 'normal';
            } else {
                fileChosenLabel.textContent = 'Nie wybrano pliku.';
                fileChosenLabel.style.opacity = '0.7';
                fileChosenLabel.style.fontStyle = 'italic';
            }
        });
    }

    // 3. Obsługa przycisku "Wdróż aktualizację" (przeniesione z poprzedniej odpowiedzi)
    const deployBtn = document.getElementById('deploy-all-btn');
    if (deployBtn) {
        deployBtn.addEventListener('click', function() {
            if (!confirm('Czy na pewno chcesz zlecić aktualizację agenta na WSZYSTKICH komputerach? Ta akcja jest nieodwracalna.')) {
                return;
            }

            const originalText = this.textContent;
            this.textContent = 'Wdrażanie...';
            this.disabled = true;

            fetch('/api/agent/deploy_update', { method: 'POST' })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.message || 'Błąd serwera') });
                    }
                    return response.json();
                })
                .then(data => {
                    alert(data.message);
                })
                .catch(error => {
                    console.error("Błąd wdrażania aktualizacji:", error);
                    alert(`Wystąpił błąd: ${error.message}`);
                })
                .finally(() => {
                    this.textContent = 'Wdróż aktualizację na wszystkich komputerach';
                    this.disabled = false;
                });
        });
    }
});