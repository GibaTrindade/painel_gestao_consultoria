(() => {
    const menu = document.querySelector('.mobile-menu-toggle');
    if (menu) menu.addEventListener('click', () => {
        const expanded = menu.getAttribute('aria-expanded') !== 'true';
        menu.setAttribute('aria-expanded', String(expanded));
        menu.closest('.sidebar').classList.toggle('menu-expanded', expanded);
    });

    document.querySelectorAll('table').forEach(table => {
        if (table.closest('.table-scroll, .results-table-scroll')) return;
        const wrapper = document.createElement('div');
        wrapper.className = 'table-scroll';
        wrapper.tabIndex = 0;
        wrapper.setAttribute('role', 'region');
        wrapper.setAttribute('aria-label', table.closest('section, article')?.querySelector('h3, h2')?.textContent || 'Tabela de dados');
        table.before(wrapper);
        wrapper.append(table);
    });

    let activeDialog = null;
    let previousFocus = null;
    const focusable = dialog => [...dialog.querySelectorAll('a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]')].filter(el => el.getClientRects().length);
    function updateDialog() {
        const dialog = [...document.querySelectorAll('.modal-backdrop')].find(el => !el.hidden && el.getClientRects().length);
        if (dialog === activeDialog) return;
        if (activeDialog) {
            document.body.classList.remove('dialog-open');
            previousFocus?.focus();
        }
        activeDialog = dialog || null;
        if (!dialog) return;
        previousFocus = document.activeElement;
        const card = dialog.querySelector('.modal-card');
        card.setAttribute('role', 'dialog');
        card.setAttribute('aria-modal', 'true');
        const heading = card.querySelector('h3');
        if (heading) {
            heading.id ||= 'dialog-title';
            card.setAttribute('aria-labelledby', heading.id);
        }
        card.tabIndex = -1;
        dialog.querySelectorAll('.modal-close').forEach(el => el.setAttribute('aria-label', 'Fechar janela'));
        document.body.classList.add('dialog-open');
        (focusable(dialog).find(el => ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) || focusable(dialog)[0] || card).focus();
    }
    new MutationObserver(updateDialog).observe(document.body, {subtree: true, attributes: true, attributeFilter: ['hidden']});
    updateDialog();
    document.addEventListener('keydown', event => {
        if (!activeDialog) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            activeDialog.querySelector('.modal-close')?.click();
        }
        if (event.key === 'Tab') {
            const items = focusable(activeDialog);
            if (!items.length) { event.preventDefault(); return; }
            const first = items[0], last = items[items.length - 1];
            if (event.shiftKey && (document.activeElement === first || !activeDialog.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
    });
    document.querySelectorAll('form').forEach(form => form.addEventListener('submit', event => queueMicrotask(() => {
        if (event.defaultPrevented || form.dataset.submitting) return;
        const submit = event.submitter;
        if (submit && !submit.hasAttribute('formnovalidate')) {
            form.dataset.submitting = 'true';
            submit.setAttribute('aria-busy', 'true');
            submit.disabled = true;
        }
    })));
    window.addEventListener('pageshow', () => {
        document.querySelectorAll('form[data-submitting]').forEach(form => {
            delete form.dataset.submitting;
            form.querySelectorAll('[aria-busy=true]').forEach(button => {
                button.disabled = false;
                button.removeAttribute('aria-busy');
            });
        });
    });
})();
