let chartZonas, chartCategoria, chartSla;

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

                // Badge de fechas / SLA (Sección 6.3 de la metodología MERC-PD)
                let badgeSla = '';
                if (riesgo.estado_tratamiento === 'Sin Tratamiento' && riesgo.fecha_limite_tratamiento) {
                    if (riesgo.vencido) {
                        badgeSla = `<span style="color: var(--color-danger); font-weight:700;">⚠ Plazo vencido (límite: ${riesgo.fecha_limite_tratamiento})</span>`;
                    } else {
                        badgeSla = `<span style="color: var(--color-text-muted);">Plazo límite: ${riesgo.fecha_limite_tratamiento} (${riesgo.dias_restantes} días restantes)</span>`;
                    }
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
                                Estado: <strong>${riesgo.estado_tratamiento}</strong> · Detectado: ${riesgo.fecha_deteccion}
                            </p>
                            <p style="margin:2px 0 0 0; font-size:0.8em;">${badgeSla}</p>
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

function cargarKpisYGraficos() {
    fetch('/api/riesgos/kpis/')
        .then(response => response.json())
        .then(data => {
            // --- Tarjetas de KPIs ---
            const kpiContenedor = document.getElementById('kpi-cards');
            kpiContenedor.innerHTML = `
                <div class="card-riesgo" style="flex-direction:column; align-items:flex-start;">
                    <p style="margin:0; font-size:0.75rem; color:var(--color-text-muted); text-transform:uppercase;">Total de Riesgos</p>
                    <h3 style="margin:4px 0 0 0;">${data.total_escenarios}</h3>
                </div>
                <div class="card-riesgo" style="flex-direction:column; align-items:flex-start;">
                    <p style="margin:0; font-size:0.75rem; color:var(--color-text-muted); text-transform:uppercase;">Índice de Riesgo Residual Promedio (IRRP)</p>
                    <h3 style="margin:4px 0 0 0;">${data.irrp.toFixed(2)}</h3>
                </div>
                <div class="card-riesgo" style="flex-direction:column; align-items:flex-start;">
                    <p style="margin:0; font-size:0.75rem; color:var(--color-text-muted); text-transform:uppercase;">% Críticos sin Control</p>
                    <h3 style="margin:4px 0 0 0; color: ${data.pct_criticos_sin_control > 0 ? 'var(--color-danger)' : 'var(--color-success)'};">${data.pct_criticos_sin_control}%</h3>
                </div>
                <div class="card-riesgo" style="flex-direction:column; align-items:flex-start;">
                    <p style="margin:0; font-size:0.75rem; color:var(--color-text-muted); text-transform:uppercase;">Escenarios con Plazo Vencido</p>
                    <h3 style="margin:4px 0 0 0; color: ${data.sla.vencidos > 0 ? 'var(--color-danger)' : 'var(--color-success)'};">${data.sla.vencidos}</h3>
                </div>
            `;

            // --- Gráfico 1: Distribución de riesgos por nivel (dona) ---
            const zonas = data.distribucion_zonas;
            if (chartZonas) chartZonas.destroy();
            chartZonas = new Chart(document.getElementById('chart-zonas'), {
                type: 'doughnut',
                data: {
                    labels: ['Bajo', 'Medio', 'Alto', 'Crítico'],
                    datasets: [{
                        data: [zonas.Bajo, zonas.Medio, zonas.Alto, zonas.Critico],
                        backgroundColor: ['#16a34a', '#d97706', '#f97316', '#dc2626'],
                    }],
                },
                options: { plugins: { legend: { position: 'bottom' } } },
            });

            // --- Gráfico 2: Riesgo acumulado por categoría de activo (barras) ---
            const categorias = Object.keys(data.riesgo_por_categoria);
            const valoresCategoria = Object.values(data.riesgo_por_categoria);
            if (chartCategoria) chartCategoria.destroy();
            chartCategoria = new Chart(document.getElementById('chart-categoria'), {
                type: 'bar',
                data: {
                    labels: categorias,
                    datasets: [{
                        label: 'Riesgo acumulado',
                        data: valoresCategoria,
                        backgroundColor: '#4f46e5',
                    }],
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true } },
                },
            });

            // --- Gráfico 3: Cumplimiento de SLA (dona) ---
            if (chartSla) chartSla.destroy();
            chartSla = new Chart(document.getElementById('chart-sla'), {
                type: 'doughnut',
                data: {
                    labels: ['En Plazo', 'Vencidos'],
                    datasets: [{
                        data: [data.sla.en_plazo, data.sla.vencidos],
                        backgroundColor: ['#16a34a', '#dc2626'],
                    }],
                },
                options: { plugins: { legend: { position: 'bottom' } } },
            });
        })
        .catch(error => console.error('Error al cargar los KPIs:', error));
}

// Cargar al iniciar y asignar evento al botón de actualizar
document.addEventListener("DOMContentLoaded", () => {
    cargarDashboard();
    cargarKpisYGraficos();
});
document.getElementById('btn-actualizar').addEventListener('click', () => {
    cargarDashboard();
    cargarKpisYGraficos();
});