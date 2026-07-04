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
        if(result.success) {
            divResultado.innerHTML = `<strong>Éxito:</strong> Activo registrado. Valor del Activo (VA) calculado: ${result.va.toFixed(2)}`;
            divResultado.style.color = 'green';
            document.getElementById('form-activo').reset();
        } else {
            divResultado.innerHTML = `<strong>Error:</strong> ${result.message}`;
            divResultado.style.color = 'red';
        }
    })
    .catch(error => console.error('Error en la petición Fetch:', error));
});