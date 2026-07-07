document.addEventListener("DOMContentLoaded", () => {
    fetch('/api/auditoria/lista/')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#tabla-auditoria tbody');
            tbody.innerHTML = '';
            (data.auditoria || []).forEach(a => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${a.fecha}</td>
                    <td>${a.tabla}</td>
                    <td>${a.accion}</td>
                    <td>${a.usuario}</td>
                    <td>${a.detalle || '—'}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(error => console.error('Error al cargar la auditoría:', error));
});