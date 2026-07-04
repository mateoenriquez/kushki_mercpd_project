// Carga dinámica de catálogos reales (Activos, Amenazas, Vulnerabilidades)
// desde SQL Server al iniciar la pantalla.
document.addEventListener("DOMContentLoaded", () => {

    function poblarSelect(selectEl, items, valueKey, labelFn, placeholder) {
        selectEl.innerHTML = '';
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

    // Activos
    fetch('/api/activos/lista/')
        .then(response => response.json())
        .then(data => {
            poblarSelect(
                document.getElementById('activo_id'),
                data.activos,
                'id',
                a => `${a.nombre} (VA: ${a.va})`,
                'un activo'
            );
        })
        .catch(error => console.error('Error al cargar activos:', error));

    // Amenazas (catálogo real de SQL Server)
    fetch('/api/amenazas/lista/')
        .then(response => response.json())
        .then(data => {
            poblarSelect(
                document.getElementById('amenaza_id'),
                data.amenazas,
                'id',
                a => `${a.nombre} (${a.tipo})`,
                'una amenaza'
            );
        })
        .catch(error => console.error('Error al cargar amenazas:', error));

    // Vulnerabilidades (catálogo real de SQL Server)
    fetch('/api/vulnerabilidades/lista/')
        .then(response => response.json())
        .then(data => {
            poblarSelect(
                document.getElementById('vulnerabilidad_id'),
                data.vulnerabilidades,
                'id',
                v => `${v.nombre} (${v.tipo})`,
                'una vulnerabilidad'
            );
        })
        .catch(error => console.error('Error al cargar vulnerabilidades:', error));
});

document.getElementById('form-riesgo').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    fetch('/api/riesgos/evaluar/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': data.csrfmiddlewaretoken
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const divResultado = document.getElementById('resultado-riesgo');
        divResultado.classList.remove('hidden');
        if (result.success) {
            divResultado.innerHTML = `<strong>Éxito:</strong> Riesgo calculado. Puntaje Final: ${result.riesgo_total.toFixed(2)}`;
            divResultado.style.color = 'green';
            this.reset();
        } else {
            divResultado.innerHTML = `<strong>Error:</strong> ${result.message}`;
            divResultado.style.color = 'red';
        }
    })
    .catch(error => console.error('Error al registrar riesgo:', error));
});