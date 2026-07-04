// Cargar activos dinámicamente al iniciar
document.addEventListener("DOMContentLoaded", () => {
    fetch('/api/activos/lista/')
        .then(response => response.json())
        .then(data => {
            const selectActivo = document.getElementById('activo_id');
            data.activos.forEach(activo => {
                let option = document.createElement('option');
                option.value = activo.id;
                option.textContent = `${activo.nombre} (VA: ${activo.va})`;
                selectActivo.appendChild(option);
            });
        });
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
        if(result.success) {
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