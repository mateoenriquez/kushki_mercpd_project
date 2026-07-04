document.addEventListener("DOMContentLoaded", () => {
    fetch('/api/escenarios/lista/')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('escenario_id');
            select.innerHTML = '';

            const optDefault = document.createElement('option');
            optDefault.value = '';
            optDefault.disabled = true;
            optDefault.selected = true;
            optDefault.textContent = 'Seleccione un escenario...';
            select.appendChild(optDefault);

            (data.escenarios || []).forEach(e => {
                const option = document.createElement('option');
                option.value = e.id;
                option.textContent = e.etiqueta;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error al cargar escenarios:', error));

    cargarComunicaciones();
});

function cargarComunicaciones() {
    fetch('/api/comunicaciones/lista/')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#tabla-comunicaciones tbody');
            tbody.innerHTML = '';

            (data.comunicaciones || []).forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${c.fecha}</td>
                    <td>${c.tipo === 'Observacion' ? 'Observación' : 'Recomendación'}</td>
                    <td>${c.contenido}</td>
                    <td>${c.usuario}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(error => console.error('Error al cargar comunicaciones:', error));
}

document.getElementById('form-comunicacion').addEventListener('submit', function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    fetch('/api/comunicaciones/registrar/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': data.csrfmiddlewaretoken
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const div = document.getElementById('resultado-comunicacion');
        div.classList.remove('hidden');
        if (result.success) {
            div.innerHTML = `<strong>Éxito:</strong> Registro guardado.`;
            div.style.color = 'green';
            this.reset();
            cargarComunicaciones();
        } else {
            div.innerHTML = `<strong>Error:</strong> ${result.message}`;
            div.style.color = 'red';
        }
    })
    .catch(error => console.error('Error en la petición Fetch:', error));
});