// Cargar catálogo de usuarios (custodios) al iniciar la pantalla.
// El campo es opcional: se agrega una opción "Sin asignar" además de los usuarios reales.
// Si la petición falla, el select se libera igual para no bloquear el formulario.
document.addEventListener("DOMContentLoaded", () => {
    const selectCustodio = document.getElementById('custodio_id');

    fetch('/api/usuarios/lista/')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            selectCustodio.innerHTML = '';

            const optSinAsignar = document.createElement('option');
            optSinAsignar.value = '';
            optSinAsignar.selected = true;
            optSinAsignar.textContent = 'Sin asignar';
            selectCustodio.appendChild(optSinAsignar);

            (data.usuarios || []).forEach(usuario => {
                const option = document.createElement('option');
                option.value = usuario.id;
                option.textContent = `${usuario.nombre} (${usuario.rol})`;
                selectCustodio.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error al cargar usuarios/custodios:', error);
            selectCustodio.innerHTML = '';
            const optError = document.createElement('option');
            optError.value = '';
            optError.selected = true;
            optError.textContent = 'Sin asignar (catálogo no disponible)';
            selectCustodio.appendChild(optError);
        });
});

document.getElementById('form-activo').addEventListener('submit', function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    // Validación estricta del rango (1 al 3) en Frontend
    if (data.confidencialidad < 1 || data.confidencialidad > 3 ||
        data.integridad < 1 || data.integridad > 3 ||
        data.disponibilidad < 1 || data.disponibilidad > 3) {
        alert('Error: Los valores de la triada CIA deben estar entre 1 y 3.');
        return;
    }

    fetch('/api/activos/registrar/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': data.csrfmiddlewaretoken
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const divResultado = document.getElementById('resultado-va');
        divResultado.classList.remove('hidden');
        if (result.success) {
            divResultado.innerHTML = `<strong>Éxito:</strong> Activo registrado. Valor del Activo (VA) calculado: ${result.va.toFixed(2)}`;
            divResultado.style.backgroundColor = 'var(--color-success-bg)';
            divResultado.style.color = 'var(--color-success)';
            divResultado.style.borderColor = 'var(--color-success)';
            document.getElementById('form-activo').reset();
        } else {
            divResultado.innerHTML = `<strong>Error:</strong> ${result.message}`;
            divResultado.style.backgroundColor = 'var(--color-danger-bg)';
            divResultado.style.color = 'var(--color-danger)';
            divResultado.style.borderColor = 'var(--color-danger)';
        }
    })
    .catch(error => console.error('Error en la petición Fetch:', error));
});