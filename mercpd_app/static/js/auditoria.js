function crearCelda(texto) {
    const td = document.createElement('td');
    td.textContent = texto ?? '—';
    return td;
}

document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/auditoria/lista/')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#tabla-auditoria tbody');
            if (!tbody) return;
            tbody.replaceChildren();

            (data.auditoria || []).forEach(a => {
                const tr = document.createElement('tr');
                tr.appendChild(crearCelda(a.fecha));
                tr.appendChild(crearCelda(a.tabla));
                tr.appendChild(crearCelda(a.accion));
                tr.appendChild(crearCelda(a.usuario));
                tr.appendChild(crearCelda(a.detalle || '—'));
                tbody.appendChild(tr);
            });
        })
        .catch(error => console.error('Error al cargar la auditoría:', error));
});
