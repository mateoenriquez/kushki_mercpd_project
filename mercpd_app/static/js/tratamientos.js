function mostrarResultado(elemento, mensaje, esExito = true) {
    elemento.classList.remove('hidden');
    elemento.textContent = mensaje;
    elemento.style.backgroundColor = esExito ? 'var(--color-success-bg)' : 'var(--color-danger-bg)';
    elemento.style.color = esExito ? 'var(--color-success)' : 'var(--color-danger)';
    elemento.style.borderColor = esExito ? 'var(--color-success)' : 'var(--color-danger)';
}

document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('escenario_id');
    fetch('/api/escenarios/lista/')
        .then(response => response.json())
        .then(data => {
            select.replaceChildren();
            if (!data.escenarios || data.escenarios.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.disabled = true;
                opt.selected = true;
                opt.textContent = 'No hay escenarios registrados';
                select.appendChild(opt);
                return;
            }

            const optDefault = document.createElement('option');
            optDefault.value = '';
            optDefault.disabled = true;
            optDefault.selected = true;
            optDefault.textContent = 'Seleccione un escenario...';
            select.appendChild(optDefault);

            data.escenarios.forEach(e => {
                const option = document.createElement('option');
                option.value = e.id;
                option.textContent = e.etiqueta;
                select.appendChild(option);
            });

            const escenarioPreseleccionado = new URLSearchParams(window.location.search).get('escenario_id');
            if (escenarioPreseleccionado) {
                select.value = escenarioPreseleccionado;
                document.getElementById('opcion_tratamiento')?.focus();
            }
        })
        .catch(error => console.error('Error al cargar escenarios:', error));

    const form = document.getElementById('form-tratamiento');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        const div = document.getElementById('resultado-tratamiento');

        fetch('/api/tratamientos/registrar/', {
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
                    mostrarResultado(div, `Éxito: Tratamiento registrado. Riesgo residual calculado: ${Number(result.riesgo_residual).toFixed(3)}`);
                    form.reset();
                } else {
                    mostrarResultado(div, `Error: ${result.message || 'No se pudo registrar el tratamiento.'}`, false);
                }
            })
            .catch(error => {
                console.error('Error en la petición Fetch:', error);
                mostrarResultado(div, 'Error: No se pudo conectar con el servidor.', false);
            });
    });
});
