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

                // Corrección #3: detalle del control aplicado y su eficacia,
                // visible para cualquier rol que vea esta tarjeta (incluye
                // al Custodio de Activo, que antes no tenía este dato).
                let detalleControl = '';
                if (riesgo.control_aplicado) {
                    detalleControl = `<p style="margin:2px 0 0 0; font-size:0.8em; color:#555;">Control aplicado: <strong>${riesgo.control_aplicado}</strong> (eficacia: ${(riesgo.eficacia_control * 100).toFixed(0)}%)</p>`;
                }

                // Corrección #2: acción rápida "Tratar este riesgo →", solo
                // visible para roles que pueden acceder a /tratamientos/
                // (window.PUEDE_TRATAR se define en dashboard.html).
                let accionRapida = '';
                if (window.PUEDE_TRATAR && riesgo.estado_tratamiento === 'Sin Tratamiento') {
                    accionRapida = `<a href="/tratamientos/?escenario_id=${riesgo.escenario_id}" style="font-size:0.8em; color: var(--color-primary); font-weight:600; text-decoration:none;">Tratar este riesgo →</a>`;
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
                            ${detalleControl}
                            <p style="margin:2px 0 0 0; font-size:0.8em;">${badgeSla}</p>
                            <p style="margin:4px 0 0 0;">${accionRapida}</p>
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
            const mttmGlobal = data.mttm.global_dias;
            const mttmTexto = mttmGlobal !== null ? `${mttmGlobal.toFixed(2)} días` : 'Sin datos';

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
                <div class="card-riesgo" style="flex-direction:column; align-items:flex-start;">
                    <p style="margin:0; font-size:0.75rem; color:var(--color-text-muted); text-transform:uppercase;">Tiempo Medio de Mitigación (MTTM)</p>
                    <h3 style="margin:4px 0 0 0;">${mttmTexto}</h3>
                </div>
            `;

            // --- Tabla de cumplimiento de MTTM por nivel de riesgo (Sección 7.3) ---
            const mttmDetalle = document.getElementById('mttm-detalle');
            if (mttmDetalle) {
                const niveles = ['Critico', 'Alto', 'Medio', 'Bajo'];
                const etiquetas = { Critico: 'Crítico', Alto: 'Alto', Medio: 'Medio', Bajo: 'Bajo' };

                let filas = '';
                niveles.forEach(nivel => {
                    const info = data.mttm.por_nivel[nivel];
                    const promedio = info.promedio_dias !== null ? `${info.promedio_dias.toFixed(2)} días` : '—';
                    const meta = info.meta_dias !== null ? `≤ ${info.meta_dias} días` : 'No aplica';
                    let estado = '<span style="color: var(--color-text-muted);">Sin muestras</span>';
                    if (info.promedio_dias !== null && info.meta_dias !== null) {
                        estado = info.cumple_meta
                            ? '<span class="badge riesgo-bajo">Cumple</span>'
                            : '<span class="badge riesgo-critico">No cumple</span>';
                    } else if (info.promedio_dias !== null) {
                        estado = '<span style="color: var(--color-text-muted);">Sin meta definida</span>';
                    }
                    filas += `
                        <tr>
                            <td>${etiquetas[nivel]}</td>
                            <td>${promedio}</td>
                            <td>${meta}</td>
                            <td>${estado}</td>
                            <td>${info.muestras}</td>
                        </tr>`;
                });

                mttmDetalle.innerHTML = `
                    <h3 style="margin-top:0;">Cumplimiento de Tiempos de Mitigación (MTTM)</h3>
                    <table>
                        <thead>
                            <tr><th>Nivel</th><th>MTTM Real</th><th>Meta (Sección 6.3/7.3)</th><th>Estado</th><th>Escenarios tratados</th></tr>
                        </thead>
                        <tbody>${filas}</tbody>
                    </table>
                `;
            }

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