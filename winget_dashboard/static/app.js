// Czekaj, aż cała strona się załaduje, zanim podepniesz skrypty do przycisków
document.addEventListener('DOMContentLoaded', () => {

    // Logika dla przełącznika motywu
    const toggleButton = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;
    if(toggleButton) {
        toggleButton.addEventListener('click', () => {
            htmlEl.classList.toggle('dark-mode');
            localStorage.setItem('theme', htmlEl.classList.contains('dark-mode') ? 'dark' : 'light');
        });
    }

    // Logika dla przycisku Odśwież (działa na index.html i computer.html)
    document.querySelectorAll('.refresh-btn').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const notificationBar = document.getElementById('notification-bar');
            const buttonCell = this.parentElement;

            this.textContent = 'Wysyłanie...';
            this.disabled = true;

            fetch(`/api/computer/${computerId}/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.textContent = 'Zlecono';
                    let message = `Zlecono odświeżenie. Strona przeładuje się automatycznie za ~35 sekund.`;
                    if (notificationBar) {
                        notificationBar.textContent = message;
                        notificationBar.style.backgroundColor = '#007bff';
                        notificationBar.style.display = 'block';
                    } else if(buttonCell) {
                         buttonCell.innerHTML = `<span class="status-pending">${message}</span>`;
                    }
                    setTimeout(() => { location.reload(); }, 35000);
                } else {
                    this.textContent = 'Błąd!';
                    this.disabled = false;
                }
            }).catch(error => {
                console.error("Błąd sieci:", error);
                this.textContent = 'Błąd sieci!';
                this.disabled = false;
            });
        });
    });

    // Logika dla przycisków "Aktualizuj" (tylko na computer.html)
    document.querySelectorAll('.update-btn:not(.uninstall-btn)').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const updateId = this.dataset.updateId;
            const packageId = this.dataset.packageId;
            const appName = this.closest('tr').cells[1].textContent;
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
                if (data.status === 'success') {
                    this.textContent = 'Zlecono';
                    setTimeout(() => location.reload(), 15000);
                } else {
                    this.textContent = 'Błąd!';
                    this.disabled = false;
                    alert('Wystąpił błąd po stronie serwera: ' + data.message);
                }
            }).catch(error => {
                console.error("Błąd sieci:", error);
                this.textContent = 'Błąd sieci!';
                this.disabled = false;
            });
        });
    });

    // Logika dla przycisków "Odinstaluj" (tylko na computer.html)
    document.querySelectorAll('.uninstall-btn').forEach(button => {
        button.addEventListener('click', function() {
            const computerId = this.dataset.computerId;
            const packageId = this.dataset.packageId;
            const appName = this.closest('tr').cells[0].textContent;
            const notificationBar = document.getElementById('notification-bar');
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
                if (data.status === 'success') {
                    this.textContent = 'Zlecono';
                    notificationBar.textContent = `Zlecono deinstalację dla "${appName}". Strona odświeży się za chwilę.`;
                    notificationBar.style.backgroundColor = '#ffc107';
                    notificationBar.style.display = 'block';
                    setTimeout(() => { location.reload(); }, 20000);
                } else {
                    this.textContent = 'Błąd!';
                    this.disabled = false;
                    notificationBar.textContent = `Wystąpił błąd podczas zlecania deinstalacji: ${data.message}`;
                    notificationBar.style.backgroundColor = '#dc3545';
                    notificationBar.style.display = 'block';
                }
            }).catch(error => {
                console.error("Błąd sieci:", error);
                this.textContent = 'Błąd sieci!';
                this.disabled = false;
            });
        });
    });

    // POPRAWIONA LOGIKA: Obsługa formularza czarnej listy
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
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // POPRAWKA: Zamiast przeładowywać, informujemy użytkownika, co ma zrobić.
                    notificationBar.textContent = 'Zapisano! Kliknij [Odśwież] w prawym górnym rogu, aby pobrać nowe dane.';
                    notificationBar.style.backgroundColor = '#28a745';
                    notificationBar.style.display = 'block';
                    window.scrollTo(0, 0);

                    button.textContent = 'Zapisano!';
                    setTimeout(() => {
                        button.textContent = originalButtonText;
                        button.disabled = false;
                    }, 2000);
                } else {
                    notificationBar.textContent = 'Błąd zapisu: ' + (data.message || 'Nieznany błąd serwera.');
                    notificationBar.style.backgroundColor = '#dc3545';
                    notificationBar.style.display = 'block';
                    window.scrollTo(0, 0);
                    button.textContent = originalButtonText;
                    button.disabled = false;
                }
            }).catch(error => {
                console.error("Błąd sieci:", error);
                notificationBar.textContent = 'Błąd sieciowy. Sprawdź konsolę przeglądarki.';
                notificationBar.style.backgroundColor = '#dc3545';
                notificationBar.style.display = 'block';
                window.scrollTo(0, 0);
                button.textContent = originalButtonText;
                button.disabled = false;
            });
        });
    }
});
