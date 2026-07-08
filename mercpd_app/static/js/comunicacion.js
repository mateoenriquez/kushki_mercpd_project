function crearCelda(texto) {
    const td = document.createElement('td');
    td.textContent = texto ?? '—';
    return td;
}

function mostrarResultado(elemento, mensaje, esExito = true) {
    if (!elemento) return;
    elemento.classList.remove('hidden');
    elemento.textContent = mensaje;
    elemento.style.backgroundColor = esExito ? 'var(--color-success-bg)' : 'var(--color-danger-bg)';
    elemento.style.color = esExito ? 'var(--color-success)' : 'var(--color-danger)';
    elemento.style.borderColor = esExito ? 'var(--color-success)' : 'var(--color-danger)';
}

function cargarEscenarios() {
    const select = document.getElementById('escenario_id');
    if (!select) return;

    fetch('/api/escenarios/lista/')
        .then(response => response.json())
        .then(data => {
            const optDefault = document.createElement('option');
            optDefault.value = '';
            optDefault.disabled = true;
            optDefault.selected = true;
            optDefault.textContent = 'Seleccione un escenario...';
            select.replaceChildren(optDefault);

            (data.escenarios || []).forEach(e => {
                const option = document.createElement('option');
                option.value = e.id;
                option.textContent = e.etiqueta;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error al cargar escenarios:', error));
}

function cargarComunicaciones() {
    fetch('/api/comunicaciones/lista/')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#tabla-comunicaciones tbody');
            if (!tbody) return;
            tbody.replaceChildren();

            (data.comunicaciones || []).forEach(c => {
                const tr = document.createElement('tr');
                tr.appendChild(crearCelda(c.fecha));
                tr.appendChild(crearCelda(c.tipo === 'Observacion' ? 'Observación' : 'Recomendación'));
                tr.appendChild(crearCelda(c.contenido));
                tr.appendChild(crearCelda(c.usuario));
                tbody.appendChild(tr);
            });
        })
        .catch(error => console.error('Error al cargar comunicaciones:', error));
}

document.addEventListener('DOMContentLoaded', () => {
    cargarEscenarios();
    cargarComunicaciones();

    const form = document.getElementById('form-comunicacion');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        const div = document.getElementById('resultado-comunicacion');

        fetch('/api/comunicaciones/registrar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': data.csrfmiddlewaretoken,
            },
            body: JSON.stringify(data),
        })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    mostrarResultado(div, 'Éxito: Registro guardado.');
                    form.reset();
                    cargarComunicaciones();
                } else {
                    mostrarResultado(div, `Error: ${result.message || 'No se pudo registrar la comunicación.'}`, false);
                }
            })
            .catch(error => {
                console.error('Error en la petición Fetch:', error);
                mostrarResultado(div, 'Error: No se pudo conectar con el servidor.', false);
            });
    });
});
