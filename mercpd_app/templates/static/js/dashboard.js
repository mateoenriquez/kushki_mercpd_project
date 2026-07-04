function cargarDashboard() {
    const contenedor = document.getElementById('contenedor-riesgos');
    contenedor.innerHTML = '<p>Actualizando semáforos de riesgo...</p>';

    fetch('/api/riesgos/dashboard/')
        .then(response => response.json())
        .then(data => {
            contenedor.innerHTML = '';
            
            if (data.riesgos.length === 0) {
                contenedor.innerHTML = '<p>No hay escenarios de riesgo registrados.</p>';
                return;
            }

            data.riesgos.forEach(riesgo => {
                // Lógica del semáforo visual
                let claseColor = '';
                let etiquetaRiesgo = '';

                // Reglas de negocio MERC-PD para colores
                if (riesgo.puntaje_total < 3.0) {
                    claseColor = 'bg-verde';
                    etiquetaRiesgo = 'Bajo';
                } else if (riesgo.puntaje_total >= 3.0 && riesgo.puntaje_total < 5.0) {
                    claseColor = 'bg-amarillo';
                    etiquetaRiesgo = 'Medio';
                } else {
                    claseColor = 'bg-rojo';
                    etiquetaRiesgo = riesgo.puntaje_total >= 7.5 ? 'Crítico' : 'Alto';
                }

                // Construcción dinámica de la tarjeta
                const card = document.createElement('div');
                card.className = 'card-riesgo';
                card.innerHTML = `
                    <div>
                        <h4 style="margin:0 0 5px 0;">Activo: ${riesgo.activo_nombre}</h4>
                        <p style="margin:0; color:#555;">Amenaza: ${riesgo.amenaza} | Vuln: ${riesgo.vulnerabilidad}</p>
                        <p style="margin:5px 0 0 0; font-size:0.9em;">
                            VA: ${riesgo.va} | Probabilidad: ${riesgo.probabilidad} | Impacto Final: ${riesgo.impacto_final.toFixed(2)}
                        </p>
                    </div>
                    <div class="semaforo ${claseColor}">
                        ${etiquetaRiesgo} (${riesgo.puntaje_total.toFixed(2)})
                    </div>
                `;
                contenedor.appendChild(card);
            });
        })
        .catch(error => {
            console.error('Error al cargar el dashboard:', error);
            contenedor.innerHTML = '<p style="color:red;">Error al conectar con la base de datos SQL Server.</p>';
        });
}

// Cargar al iniciar y asignar evento al botón de actualizar
document.addEventListener("DOMContentLoaded", cargarDashboard);
document.getElementById('btn-actualizar').addEventListener('click', cargarDashboard);