document.addEventListener("DOMContentLoaded", () => {
    fetch('/api/escenarios/lista/')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('escenario_id');
            select.innerHTML = '';

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
        })
        .catch(error => console.error('Error al cargar escenarios:', error));
});

document.getElementById('form-tratamiento').addEventListener('submit', function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    fetch('/api/tratamientos/registrar/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': data.csrfmiddlewaretoken
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const div = document.getElementById('resultado-tratamiento');
        div.classList.remove('hidden');
        if (result.success) {
            div.innerHTML = `<strong>Éxito:</strong> Tratamiento registrado. Riesgo Residual calculado: ${result.riesgo_residual.toFixed(3)}`;
            div.style.backgroundColor = 'var(--color-success-bg)';
            div.style.color = 'var(--color-success)';
            div.style.borderColor = 'var(--color-success)';
            this.reset();
        } else {
            div.innerHTML = `<strong>Error:</strong> ${result.message}`;
            div.style.backgroundColor = 'var(--color-danger-bg)';
            div.style.color = 'var(--color-danger)';
            div.style.borderColor = 'var(--color-danger)';
        }
    })
    .catch(error => console.error('Error en la petición Fetch:', error));
});