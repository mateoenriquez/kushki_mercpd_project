function cargarDashboard() {
    const contenedor = document.getElementById('contenedor-riesgos');
    const btnActualizar = document.getElementById('btn-actualizar');
    
    // 1. Mostrar mensaje de carga y bloquear el botón para evitar múltiples clics
    contenedor.innerHTML = '<p>Actualizando semáforos de riesgo...</p>';
    btnActualizar.disabled = true;
    btnActualizar.innerText = 'Cargando...';

    fetch('/api/riesgos/dashboard/')
        .then(response => response.json())
        .then(data => {
            contenedor.innerHTML = '';
            
            if (data.riesgos.length === 0) {
                contenedor.innerHTML = '<p>No hay escenarios de riesgo registrados.</p>';
                return;
            }

            data.riesgos.forEach(riesgo => {
                let claseColor = '';
                let etiquetaRiesgo = '';

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

                const card = document.createElement('div');
                card.className = 'card-riesgo';
                    card.innerHTML = `
                        <div>
                            <h4 style="margin:0 0 5px 0;">Activo: ${riesgo.activo_nombre}</h4>
                            <p style="margin:0; color:#555;">Amenaza: ${riesgo.amenaza} | Vuln: ${riesgo.vulnerabilidad}</p>
                            <p style="margin:5px 0 0 0; font-size:0.9em;">
                                VA: ${riesgo.va} | Probabilidad: ${riesgo.probabilidad} | Riesgo Inherente: ${riesgo.riesgo_inherente.toFixed(2)}
                            </p>
                            <p style="margin:2px 0 0 0; font-size:0.85em; color:#555;">
                                Estado: <strong>${riesgo.estado_tratamiento}</strong>
                            </p>
                        </div>
                        <div class="semaforo ${claseColor}">
                            ${etiquetaRiesgo} (Riesgo Actual: ${riesgo.puntaje_total.toFixed(2)})
                        </div>
                    `;
                contenedor.appendChild(card);
            });
        })
        .catch(error => {
            console.error('Error al cargar el dashboard:', error);
            contenedor.innerHTML = '<p style="color:red;">Error al conectar con la base de datos SQL Server.</p>';
        })
        .finally(() => {
            // 2. Liberar el botón sin importar si hubo error o éxito
            btnActualizar.disabled = false;
            btnActualizar.innerText = 'Actualizar Dashboard';
        });
}

// Cargar al iniciar y asignar evento al botón de actualizar
document.addEventListener("DOMContentLoaded", cargarDashboard);
document.getElementById('btn-actualizar').addEventListener('click', cargarDashboard);