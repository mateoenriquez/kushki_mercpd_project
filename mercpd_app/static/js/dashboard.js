let chartZonas, chartCategoria, chartSla;

function nivelYColorDe(puntaje) {
    if (puntaje < 1.5) return { nivel: 'Muy Bajo', clase: 'bg-celeste', hex: '#0EA5E9' };
    if (puntaje < 3.0) return { nivel: 'Bajo', clase: 'bg-verde', hex: '#16A34A' };
    if (puntaje < 5.0) return { nivel: 'Medio', clase: 'bg-amarillo', hex: '#F59E0B' };
    if (puntaje < 7.5) return { nivel: 'Alto', clase: 'bg-naranja', hex: '#EA580C' };
    return { nivel: 'Crítico', clase: 'bg-rojo', hex: '#B91C1C' };
}

function cargarDashboard() {
    const tbody = document.querySelector('#tabla-riesgos tbody');

    fetch('/api/riesgos/dashboard/')
        .then(response => response.json())
        .then(data => {
            tbody.innerHTML = '';

            if (data.riesgos.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8">No hay escenarios de riesgo registrados.</td></tr>';
                return;
            }

            data.riesgos.forEach(riesgo => {
                const info = nivelYColorDe(riesgo.puntaje_total);

                let celdaPlazo = '<span class="badge-en-plazo">—</span>';

                if (riesgo.fecha_limite_tratamiento) {
                    if (riesgo.vencido) {
                        celdaPlazo = `<span class="badge-vencido">Vencido<br>${riesgo.fecha_limite_tratamiento}</span>`;
                    } else if (riesgo.estado_tratamiento === 'Sin Tratamiento') {
                        celdaPlazo = `<span class="badge-en-plazo">${riesgo.fecha_limite_tratamiento}<br>(${riesgo.dias_restantes} días)</span>`;
                    } else {
                        celdaPlazo = `<span class="badge-en-plazo">${riesgo.fecha_limite_tratamiento}</span>`;
                    }
                }

                let celdaAccion = '—';

                if (window.PUEDE_TRATAR) {
                    const textoBoton = riesgo.estado_tratamiento === 'Sin Tratamiento'
                        ? 'Tratar →'
                        : 'Nuevo →';

                    celdaAccion = `<a href="/tratamientos/?escenario_id=${riesgo.escenario_id}" class="btn-tratar">${textoBoton}</a>`;
                }

                let controlTexto = riesgo.control_aplicado
                    ? `<br><span style="font-size:0.78em; color:#555;">Control: ${riesgo.control_aplicado} (${(riesgo.eficacia_control * 100).toFixed(0)}%)</span>`
                    : '';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${riesgo.activo_nombre}</strong></td>
                    <td>${riesgo.amenaza}<br><span style="font-size:0.85em; color:#555;">${riesgo.vulnerabilidad}</span></td>
                    <td><span class="semaforo ${info.clase}" style="font-size:0.7rem; padding:5px 10px;">${info.nivel}</span></td>
                    <td>VA ${riesgo.va} · P ${riesgo.probabilidad} · R ${riesgo.puntaje_total.toFixed(2)}</td>
                    <td><strong>${riesgo.estado_tratamiento}</strong>${controlTexto}</td>
                    <td>${riesgo.fecha_deteccion}</td>
                    <td>${celdaPlazo}</td>
                    <td>${celdaAccion}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(error => {
            console.error('Error al cargar el dashboard:', error);
            tbody.innerHTML = '<tr><td colspan="8" style="color:red;">Error al conectar con la base de datos SQL Server.</td></tr>';
        });
}

function renderMttm(mttm) {
    const niveles = ['Critico', 'Alto', 'Medio', 'Bajo', 'Muy Bajo'];

    const etiquetas = {
        'Critico': 'Crítico',
        'Alto': 'Alto',
        'Medio': 'Medio',
        'Bajo': 'Bajo',
        'Muy Bajo': 'Muy Bajo'
    };

    const clases = {
        'Critico': 'bg-rojo',
        'Alto': 'bg-naranja',
        'Medio': 'bg-amarillo',
        'Bajo': 'bg-verde',
        'Muy Bajo': 'bg-celeste'
    };

    let filas = '';

    niveles.forEach(nivel => {
        const info = mttm.por_nivel[nivel] || {
            promedio_dias: null,
            meta_dias: null,
            cumple_meta: false,
            muestras: 0
        };

        const promedio = info.promedio_dias !== null
            ? `${info.promedio_dias.toFixed(2)} días`
            : '—';

        const meta = info.meta_dias !== null
            ? `Máximo ${info.meta_dias} días`
            : 'No aplica';

        let estado = '<span style="color: var(--color-text-muted);">Sin escenarios tratados</span>';

        if (info.promedio_dias !== null && info.meta_dias !== null) {
            estado = info.cumple_meta
                ? `<span class="semaforo bg-verde" style="font-size:0.7rem; padding:5px 10px;">Cumple</span>`
                : `<span class="semaforo bg-rojo" style="font-size:0.7rem; padding:5px 10px;">No cumple</span>`;
        } else if (info.promedio_dias !== null) {
            estado = '<span style="color: var(--color-text-muted);">Sin meta definida</span>';
        }

        filas += `
            <tr>
                <td>
                    <span class="semaforo ${clases[nivel]}" style="font-size:0.7rem; padding:5px 10px;">
                        ${etiquetas[nivel]}
                    </span>
                </td>
                <td>${promedio}</td>
                <td>${meta}</td>
                <td>${estado}</td>
                <td style="text-align:center; font-weight:700;">${info.muestras}</td>
            </tr>`;
    });

    document.getElementById('mttm-detalle').innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Nivel</th>
                    <th>MTTM Real (promedio)</th>
                    <th>Meta MERC-PD</th>
                    <th>Estado</th>
                    <th>Riesgos Tratados</th>
                </tr>
            </thead>
            <tbody>${filas}</tbody>
        </table>
    `;
}

function renderMatrizCalor(matriz) {
    const cont = document.getElementById('matriz-calor');

    if (!cont) return;

    const probabilidades = [3, 2, 1];
    const impactos = [1, 2, 3];

    function colorCelda(p, i) {
        const severidad = p * i;

        if (severidad <= 1) return '#0EA5E9';   // Muy Bajo
        if (severidad <= 2) return '#16A34A';   // Bajo
        if (severidad <= 4) return '#F59E0B';   // Medio
        if (severidad <= 6) return '#EA580C';   // Alto
        return '#B91C1C';                       // Crítico
    }

    let html = `<div class="matriz-eje"></div>`;

    impactos.forEach(i => {
        html += `<div class="matriz-eje">Impacto ${i}</div>`;
    });

    probabilidades.forEach(p => {
        html += `<div class="matriz-eje">Prob. ${p}</div>`;

        impactos.forEach(i => {
            const cantidad = matriz[`${p}-${i}`] || 0;

            html += `
                <div class="matriz-celda" style="background-color:${colorCelda(p, i)};">
                    ${cantidad}
                </div>
            `;
        });
    });

    cont.innerHTML = `<div class="matriz-calor">${html}</div>`;
}

function cargarKpisYGraficos() {
    fetch('/api/riesgos/kpis/')
        .then(response => response.json())
        .then(data => {
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
                    <h3 style="margin:4px 0 0 0; color: ${data.pct_criticos_sin_control > 0 ? 'var(--color-risk-critico)' : 'var(--color-success)'};">${data.pct_criticos_sin_control}%</h3>
                </div>
                <div class="card-riesgo" style="flex-direction:column; align-items:flex-start;">
                    <p style="margin:0; font-size:0.75rem; color:var(--color-text-muted); text-transform:uppercase;">Escenarios con Plazo Vencido</p>
                    <h3 style="margin:4px 0 0 0; color: ${data.sla.vencidos > 0 ? 'var(--color-risk-critico)' : 'var(--color-success)'};">${data.sla.vencidos}</h3>
                </div>
                <div class="card-riesgo" style="flex-direction:column; align-items:flex-start;">
                    <p style="margin:0; font-size:0.75rem; color:var(--color-text-muted); text-transform:uppercase;">Tiempo Medio de Mitigación (MTTM)</p>
                    <h3 style="margin:4px 0 0 0;">${mttmTexto}</h3>
                </div>
            `;

            renderMttm(data.mttm);
            renderMatrizCalor(data.matriz_calor);

                const zonas = data.distribucion_zonas;

                const labelsZonasV2 = ['Muy Bajo', 'Bajo', 'Medio', 'Alto', 'Crítico'];

                const dataZonasV2 = [
                    zonas['Muy Bajo'] || 0,
                    zonas.Bajo || 0,
                    zonas.Medio || 0,
                    zonas.Alto || 0,
                    zonas.Critico || 0
                ];

                const coloresZonasV2 = [
                    '#0EA5E9',
                    '#16A34A',
                    '#F59E0B',
                    '#EA580C',
                    '#B91C1C'
                ];

                if (chartZonas) chartZonas.destroy();

                chartZonas = new Chart(document.getElementById('chart-zonas'), {
                    type: 'doughnut',
                    data: {
                        labels: labelsZonasV2,
                        datasets: [{
                            data: dataZonasV2,
                            backgroundColor: coloresZonasV2,
                        }],
                    },
                    options: {
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    },
                });

            const categorias = Object.keys(data.riesgo_por_categoria);
            const valoresCategoria = Object.values(data.riesgo_por_categoria);
            if (chartCategoria) chartCategoria.destroy();
            chartCategoria = new Chart(document.getElementById('chart-categoria'), {
                type: 'bar',
                data: {
                    labels: categorias,
                    datasets: [{ label: 'Riesgo acumulado', data: valoresCategoria, backgroundColor: '#146C94' }],
                },
                options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
            });

            if (chartSla) chartSla.destroy();
            chartSla = new Chart(document.getElementById('chart-sla'), {
                type: 'doughnut',
                data: {
                    labels: ['En Plazo', 'Vencidos'],
                    datasets: [{ data: [data.sla.en_plazo, data.sla.vencidos], backgroundColor: ['#16A34A', '#B91C1C'] }],
                },
                options: { plugins: { legend: { position: 'bottom' } } },
            });
        })
        .catch(error => console.error('Error al cargar los KPIs:', error));
}

document.addEventListener("DOMContentLoaded", () => {
    cargarDashboard();
    cargarKpisYGraficos();
});

document.getElementById('btn-actualizar').addEventListener('click', function () {
    this.classList.add('girando');
    cargarDashboard();
    cargarKpisYGraficos();
    setTimeout(() => this.classList.remove('girando'), 600);
});