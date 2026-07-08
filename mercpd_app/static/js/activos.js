function mostrarResultado(elemento, mensaje, esExito = true) {
    elemento.classList.remove('hidden');
    elemento.textContent = mensaje;
    elemento.style.backgroundColor = esExito ? 'var(--color-success-bg)' : 'var(--color-danger-bg)';
    elemento.style.color = esExito ? 'var(--color-success)' : 'var(--color-danger)';
    elemento.style.borderColor = esExito ? 'var(--color-success)' : 'var(--color-danger)';
}

function crearOpcion(valor, texto, seleccionada = false) {
    const option = document.createElement('option');
    option.value = valor;
    option.textContent = texto;
    option.selected = seleccionada;
    return option;
}

document.addEventListener('DOMContentLoaded', () => {
    const selectCustodio = document.getElementById('custodio_id');
    if (!selectCustodio) return;

    fetch('/api/usuarios/lista/')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            selectCustodio.replaceChildren(crearOpcion('', 'Sin asignar', true));
            (data.usuarios || []).forEach(usuario => {
                selectCustodio.appendChild(crearOpcion(usuario.id, `${usuario.nombre} (${usuario.rol})`));
            });
        })
        .catch(error => {
            console.error('Error al cargar usuarios/custodios:', error);
            selectCustodio.replaceChildren(crearOpcion('', 'Sin asignar (catálogo no disponible)', true));
        });

    const form = document.getElementById('form-activo');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        const divResultado = document.getElementById('resultado-va');

        const c = Number(data.confidencialidad);
        const i = Number(data.integridad);
        const d = Number(data.disponibilidad);
        if (![c, i, d].every(v => Number.isInteger(v) && v >= 1 && v <= 3)) {
            mostrarResultado(divResultado, 'Error: Los valores de la triada CIA deben estar entre 1 y 3.', false);
            return;
        }

        fetch('/api/activos/registrar/', {
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
                    mostrarResultado(divResultado, `Éxito: Activo registrado. Valor del Activo (VA) calculado: ${Number(result.va).toFixed(2)}`);
                    form.reset();
                } else {
                    mostrarResultado(divResultado, `Error: ${result.message || 'No se pudo registrar el activo.'}`, false);
                }
            })
            .catch(error => {
                console.error('Error en la petición Fetch:', error);
                mostrarResultado(divResultado, 'Error: No se pudo conectar con el servidor.', false);
            });
    });
});
