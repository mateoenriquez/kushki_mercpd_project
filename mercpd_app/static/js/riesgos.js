function mostrarResultado(elemento, mensaje, esExito = true) {
    elemento.classList.remove('hidden');
    elemento.textContent = mensaje;
    elemento.style.backgroundColor = esExito ? 'var(--color-success-bg)' : 'var(--color-danger-bg)';
    elemento.style.color = esExito ? 'var(--color-success)' : 'var(--color-danger)';
    elemento.style.borderColor = esExito ? 'var(--color-success)' : 'var(--color-danger)';
}

function poblarSelect(selectEl, items, valueKey, labelFn, placeholder) {
    selectEl.replaceChildren();
    if (!items || items.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.disabled = true;
        opt.selected = true;
        opt.textContent = `No hay ${placeholder} registrados`;
        selectEl.appendChild(opt);
        return;
    }

    const optDefault = document.createElement('option');
    optDefault.value = '';
    optDefault.disabled = true;
    optDefault.selected = true;
    optDefault.textContent = `Seleccione ${placeholder}...`;
    selectEl.appendChild(optDefault);

    items.forEach(item => {
        const option = document.createElement('option');
        option.value = item[valueKey];
        option.textContent = labelFn(item);
        selectEl.appendChild(option);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const activoSelect = document.getElementById('activo_id');
    const amenazaSelect = document.getElementById('amenaza_id');
    const vulnerabilidadSelect = document.getElementById('vulnerabilidad_id');

    fetch('/api/activos/lista/')
        .then(response => response.json())
        .then(data => poblarSelect(activoSelect, data.activos, 'id', a => `${a.nombre} (VA: ${a.va})`, 'un activo'))
        .catch(error => console.error('Error al cargar activos:', error));

    fetch('/api/amenazas/lista/')
        .then(response => response.json())
        .then(data => poblarSelect(amenazaSelect, data.amenazas, 'id', a => `${a.nombre} (${a.tipo})`, 'una amenaza'))
        .catch(error => console.error('Error al cargar amenazas:', error));

    fetch('/api/vulnerabilidades/lista/')
        .then(response => response.json())
        .then(data => poblarSelect(vulnerabilidadSelect, data.vulnerabilidades, 'id', v => `${v.nombre} (${v.tipo})`, 'una vulnerabilidad'))
        .catch(error => console.error('Error al cargar vulnerabilidades:', error));

    const form = document.getElementById('form-riesgo');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        const divResultado = document.getElementById('resultado-riesgo');

        fetch('/api/riesgos/evaluar/', {
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
                    let mensaje = `Éxito: Riesgo calculado. Puntaje final: ${Number(result.riesgo_total).toFixed(2)}. Nivel: ${result.nivel_riesgo}. Plazo límite de tratamiento: ${result.fecha_limite_tratamiento}.`;
                    if (result.piso_aplicado && result.mensaje_piso) mensaje += ` ${result.mensaje_piso}`;
                    mostrarResultado(divResultado, mensaje);
                    form.reset();
                } else {
                    mostrarResultado(divResultado, `Error: ${result.message || 'No se pudo registrar el riesgo.'}`, false);
                }
            })
            .catch(error => {
                console.error('Error al registrar riesgo:', error);
                mostrarResultado(divResultado, 'Error: No se pudo conectar con el servidor.', false);
            });
    });
});
