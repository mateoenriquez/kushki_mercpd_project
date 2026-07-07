document.addEventListener("DOMContentLoaded", () => {
    // Estado de colapsado, persistente entre pantallas
    const colapsado = localStorage.getItem('argos_sidebar_colapsado') === 'true';
    if (colapsado) document.body.classList.add('sidebar-collapsed');

    document.getElementById('sidebar-toggle').addEventListener('click', () => {
        document.body.classList.toggle('sidebar-collapsed');
        localStorage.setItem('argos_sidebar_colapsado', document.body.classList.contains('sidebar-collapsed'));
    });

    // Acordeón de submenús
    document.querySelectorAll('.nav-item-btn[data-target]').forEach(btn => {
        btn.addEventListener('click', () => {
            const submenu = document.getElementById(btn.dataset.target);
            submenu.classList.toggle('open');
            btn.classList.toggle('open');
        });
    });
});