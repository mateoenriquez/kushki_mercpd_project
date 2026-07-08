let chartZonas, chartCategoria, chartSla;

function nivelYColorDe(puntaje) {
    if (puntaje < 1.5) return { nivel: 'Muy Bajo', clase: 'bg-celeste', hex: '#0EA5E9' };
    if (puntaje < 3.0) return { nivel: 'Bajo', clase: 'bg-verde', hex: '#16A34A' };
    if (puntaje < 5.0) return { nivel: 'Medio', clase: 'bg-amarillo', hex: '#F59E0B' };
    if (puntaje < 7.5) return { nivel: 'Alto', clase: 'bg-naranja', hex: '#EA580C' };
    return { nivel: 'Crítico', clase: 'bg-rojo', hex: '#B91C1C' };
}

function crearCelda(texto) {
    const td = document.createElement('td');
    td.textContent = texto ?? '—';
    return td;
}

function crearBadge(texto, clase) {
    const span = document.createElement('span');
    span.className = clase;
    span.textContent = texto;
    return span;
}

function crearCardKpi(titulo, valor, claseValor = '') {
    const card = document.createElement('div');
    card.className = 'card-riesgo kpi-card';

    const p = document.createElement('p');
    p.textContent = titulo;

    const h = document.createElement('h3');
    h.textContent = valor;
    if (claseValor) h.className = claseValor;

    card.appendChild(p);
    card.appendChild(h);
    return card;
}

function cargarDashboard() {
    const tbody = document.querySelector('#tabla-riesgos tbody');
    if (!tbody) return;

    fetch('/api/riesgos/dashboard/')
        .then(response => response.json())
        .then(data => {
            tbody.replaceChildren();
            const riesgos = data.riesgos || [];

            if (riesgos.length === 0) {
                const tr = document.createElement('tr');
                const td = crearCelda('No hay escenarios de riesgo registrados.');
                td.colSpan = 8;
                tr.appendChild(td);
                tbody.appendChild(tr);
                return;
            }

            riesgos.forEach(riesgo => {
                const info = nivelYColorDe(Number(riesgo.puntaje_total));
                const tr = document.createElement('tr');

                const tdActivo = crearCelda('');
                const activoStrong = document.createElement('strong');
                activoStrong.textContent = riesgo.activo_nombre;
                tdActivo.appendChild(activoStrong);
                tr.appendChild(tdActivo);

                const tdAmenaza = crearCelda('');
                tdAmenaza.appendChild(document.createTextNode(riesgo.amenaza || '—'));
                tdAmenaza.appendChild(document.createElement('br'));
                const vuln = document.createElement('span');
                vuln.className = 'texto-secundario';
                vuln.textContent = riesgo.vulnerabilidad || '—';
                tdAmenaza.appendChild(vuln);
                tr.appendChild(tdAmenaza);

                const tdNivel = crearCelda('');
                tdNivel.appendChild(crearBadge(info.nivel, `semaforo ${info.clase}`));
                tr.appendChild(tdNivel);

                tr.appendChild(crearCelda(`VA ${riesgo.va} · P ${riesgo.probabilidad} · R ${Number(riesgo.puntaje_total).toFixed(2)}`));

                const tdEstado = crearCelda('');
                const estado = document.createElement('strong');
                estado.textContent = riesgo.estado_tratamiento || 'Sin Tratamiento';
                tdEstado.appendChild(estado);
                if (riesgo.control_aplicado) {
                    tdEstado.appendChild(document.createElement('br'));
                    const control = document.createElement('span');
                    control.className = 'texto-secundario';
                    const eficacia = riesgo.eficacia_control !== null && riesgo.eficacia_control !== undefined
                        ? `${(Number(riesgo.eficacia_control) * 100).toFixed(0)}%`
                        : 'N/D';
                    control.textContent = `Control: ${riesgo.control_aplicado} (${eficacia})`;
                    tdEstado.appendChild(control);
                }
                tr.appendChild(tdEstado);

                tr.appendChild(crearCelda(riesgo.fecha_deteccion));

                const tdPlazo = crearCelda('');
                if (riesgo.fecha_limite_tratamiento) {
                    if (riesgo.vencido) {
                        tdPlazo.appendChild(crearBadge(`Vencido · ${riesgo.fecha_limite_tratamiento}`, 'badge-vencido'));
                    } else if (riesgo.estado_tratamiento === 'Sin Tratamiento') {
                        tdPlazo.appendChild(crearBadge(`${riesgo.fecha_limite_tratamiento} (${riesgo.dias_restantes} días)`, 'badge-en-plazo'));
                    } else {
                        tdPlazo.appendChild(crearBadge(riesgo.fecha_limite_tratamiento, 'badge-en-plazo'));
                    }
                } else {
                    tdPlazo.textContent = '—';
                }
                tr.appendChild(tdPlazo);

                const tdAccion = crearCelda('');
                if (window.PUEDE_TRATAR) {
                    const enlace = document.createElement('a');
                    enlace.href = `/tratamientos/?escenario_id=${encodeURIComponent(riesgo.escenario_id)}`;
                    enlace.className = 'btn-tratar';
                    enlace.textContent = riesgo.estado_tratamiento === 'Sin Tratamiento' ? 'Tratar →' : 'Nuevo →';
                    tdAccion.appendChild(enlace);
                } else {
                    tdAccion.textContent = '—';
                }
                tr.appendChild(tdAccion);

                tbody.appendChild(tr);
            });
        })
        .catch(error => {
            console.error('Error al cargar el dashboard:', error);
            const tr = document.createElement('tr');
            const td = crearCelda('Error al conectar con la base de datos SQL Server.');
            td.colSpan = 8;
            td.className = 'texto-error';
            tr.appendChild(td);
            tbody.replaceChildren(tr);
        });
}

function renderMttm(mttm) {
    const cont = document.getElementById('mttm-detalle');
    if (!cont) return;

    const niveles = ['Critico', 'Alto', 'Medio', 'Bajo', 'Muy Bajo'];
    const etiquetas = { Critico: 'Crítico', Alto: 'Alto', Medio: 'Medio', Bajo: 'Bajo', 'Muy Bajo': 'Muy Bajo' };
    const clases = { Critico: 'bg-rojo', Alto: 'bg-naranja', Medio: 'bg-amarillo', Bajo: 'bg-verde', 'Muy Bajo': 'bg-celeste' };

    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const trHead = document.createElement('tr');
    ['Nivel', 'MTTM Real (promedio)', 'Meta MERC-PD', 'Estado', 'Riesgos Tratados'].forEach(t => trHead.appendChild(crearCelda(t)));
    thead.appendChild(trHead);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    niveles.forEach(nivel => {
        const info = (mttm?.por_nivel || {})[nivel] || { promedio_dias: null, meta_dias: null, cumple_meta: false, muestras: 0 };
        const tr = document.createElement('tr');

        const tdNivel = crearCelda('');
        tdNivel.appendChild(crearBadge(etiquetas[nivel], `semaforo ${clases[nivel]}`));
        tr.appendChild(tdNivel);
        tr.appendChild(crearCelda(info.promedio_dias !== null ? `${Number(info.promedio_dias).toFixed(2)} días` : '—'));
        tr.appendChild(crearCelda(info.meta_dias !== null ? `Máximo ${info.meta_dias} días` : 'No aplica'));

        const tdEstado = crearCelda('');
        if (info.promedio_dias !== null && info.meta_dias !== null) {
            tdEstado.appendChild(crearBadge(info.cumple_meta ? 'Cumple' : 'No cumple', info.cumple_meta ? 'semaforo bg-verde' : 'semaforo bg-rojo'));
        } else {
            tdEstado.textContent = 'Sin escenarios tratados';
        }
        tr.appendChild(tdEstado);
        tr.appendChild(crearCelda(info.muestras));
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    cont.replaceChildren(table);
}

function renderMatrizCalor(matriz) {
    const cont = document.getElementById('matriz-calor');
    if (!cont) return;

    const probabilidades = [3, 2, 1];
    const impactos = [1, 2, 3];
    const wrapper = document.createElement('div');
    wrapper.className = 'matriz-calor';

    wrapper.appendChild(document.createElement('div'));
    impactos.forEach(i => {
        const eje = document.createElement('div');
        eje.className = 'matriz-eje';
        eje.textContent = `Impacto ${i}`;
        wrapper.appendChild(eje);
    });

    probabilidades.forEach(p => {
        const eje = document.createElement('div');
        eje.className = 'matriz-eje';
        eje.textContent = `Prob. ${p}`;
        wrapper.appendChild(eje);

        impactos.forEach(i => {
            const cantidad = (matriz || {})[`${p}-${i}`] || 0;
            const celda = document.createElement('div');
            celda.className = `matriz-celda ${nivelYColorDe(p * i).clase}`;
            celda.textContent = cantidad;
            wrapper.appendChild(celda);
        });
    });

    cont.replaceChildren(wrapper);
}

function cargarKpisYGraficos() {
    fetch('/api/riesgos/kpis/')
        .then(response => response.json())
        .then(data => {
            const kpiContenedor = document.getElementById('kpi-cards');
            if (!kpiContenedor) return;

            const mttmGlobal = data.mttm?.global_dias;
            const mttmTexto = mttmGlobal !== null && mttmGlobal !== undefined ? `${Number(mttmGlobal).toFixed(2)} días` : 'Sin datos';
            kpiContenedor.replaceChildren(
                crearCardKpi('Total de Riesgos', data.total_escenarios),
                crearCardKpi('Índice de Riesgo Residual Promedio (IRRP)', Number(data.irrp || 0).toFixed(2)),
                crearCardKpi('% Críticos sin Control', `${data.pct_criticos_sin_control}%`, data.pct_criticos_sin_control > 0 ? 'texto-error' : 'texto-exito'),
                crearCardKpi('Escenarios con Plazo Vencido', data.sla?.vencidos || 0, (data.sla?.vencidos || 0) > 0 ? 'texto-error' : 'texto-exito'),
                crearCardKpi('Tiempo Medio de Mitigación (MTTM)', mttmTexto),
            );

            renderMttm(data.mttm);
            renderMatrizCalor(data.matriz_calor);

            const zonas = data.distribucion_zonas || {};
            const labelsZonas = ['Muy Bajo', 'Bajo', 'Medio', 'Alto', 'Crítico'];
            const dataZonas = [zonas['Muy Bajo'] || 0, zonas.Bajo || 0, zonas.Medio || 0, zonas.Alto || 0, zonas.Critico || 0];
            const coloresZonas = ['#0EA5E9', '#16A34A', '#F59E0B', '#EA580C', '#B91C1C'];

            if (chartZonas) chartZonas.destroy();
            chartZonas = new Chart(document.getElementById('chart-zonas'), {
                type: 'doughnut',
                data: { labels: labelsZonas, datasets: [{ data: dataZonas, backgroundColor: coloresZonas }] },
                options: { plugins: { legend: { position: 'bottom' } } },
            });

            const categorias = Object.keys(data.riesgo_por_categoria || {});
            const valoresCategoria = Object.values(data.riesgo_por_categoria || {});
            if (chartCategoria) chartCategoria.destroy();
            chartCategoria = new Chart(document.getElementById('chart-categoria'), {
                type: 'bar',
                data: { labels: categorias, datasets: [{ label: 'Riesgo acumulado', data: valoresCategoria, backgroundColor: '#146C94' }] },
                options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
            });

            if (chartSla) chartSla.destroy();
            chartSla = new Chart(document.getElementById('chart-sla'), {
                type: 'doughnut',
                data: { labels: ['En Plazo', 'Vencidos'], datasets: [{ data: [data.sla?.en_plazo || 0, data.sla?.vencidos || 0], backgroundColor: ['#16A34A', '#B91C1C'] }] },
                options: { plugins: { legend: { position: 'bottom' } } },
            });
        })
        .catch(error => console.error('Error al cargar los KPIs:', error));
}

document.addEventListener('DOMContentLoaded', () => {
    cargarDashboard();
    cargarKpisYGraficos();

    const btnActualizar = document.getElementById('btn-actualizar');
    if (btnActualizar) {
        btnActualizar.addEventListener('click', function () {
            this.classList.add('girando');
            cargarDashboard();
            cargarKpisYGraficos();
            setTimeout(() => this.classList.remove('girando'), 600);
        });
    }
});
