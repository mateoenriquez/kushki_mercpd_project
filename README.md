# ARGOS MERC-PD

Sistema web que automatiza la **Metodología de Evaluación de Riesgos Cibernéticos y Protección de Datos (MERC-PD)**, aplicada al caso de estudio de una pasarela de pagos (Kushki). Permite registrar activos, valorar su criticidad, identificar y calcular riesgos, aplicar tratamientos, calcular riesgo residual y monitorear todo desde un dashboard ejecutivo.

Proyecto integrador de la asignatura **Seguridad Informática** — Universidad de Las Américas (UDLA), Carrera de Ingeniería en Software.

## Tabla de contenido

- [Descripción general](#descripción-general)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Metodología MERC-PD](#metodología-merc-pd)
- [Roles y permisos](#roles-y-permisos)
- [Instalación y ejecución local](#instalación-y-ejecución-local)
- [Estructura funcional](#estructura-funcional)
- [Capturas de pantalla](#capturas-de-pantalla)
- [Casos de prueba](#casos-de-prueba)
- [Observaciones y deuda técnica conocida](#observaciones-y-deuda-técnica-conocida)
- [Integrantes](#integrantes)

## Descripción general

ARGOS MERC-PD es la implementación en software de MERC-PD v2.0, una metodología de gestión de riesgos alineada a **ISO/IEC 27001, ISO/IEC 27005, ISO/IEC 27002:2022** y al enfoque de protección de datos personales (SPDP) exigido en el marco legal ecuatoriano. El sistema convierte un proceso de evaluación de riesgos, tradicionalmente manual, en un flujo digital con reglas de negocio validadas tanto en la aplicación (Django) como en la base de datos (SQL Server), incluyendo control de acceso basado en roles y trazabilidad completa por auditoría.

## Arquitectura

Usuario / Profesor
│ HTTPS/HTTP
▼
Frontend web (Templates HTML + JS + Chart.js)
│ rutas + API
▼
Backend Django (vistas protegidas por sesión, reglas MERC-PD v2.0, RBAC)
│ ORM / SQL
▼
SQL Server — esquema mercpd (tablas, vistas, procedimientos, triggers)

- **Servidor de aplicación:** Waitress (WSGI), ejecución local en `127.0.0.1:8080`.
- **Archivos estáticos:** WhiteNoise.
- **Publicación temporal para evaluación:** Cloudflare Tunnel / ngrok.
- **Reglas de negocio con defensa en profundidad:** validadas en el backend (Django) y reforzadas con triggers en SQL Server (por ejemplo, el bloqueo de aceptación de riesgos Altos/Críticos).

## Tecnologías

| Componente | Tecnología / versión |
|---|---|
| Backend | Django 5.0.6 |
| Conector SQL Server | mssql-django 1.7.3 + pyodbc 5.3.0 |
| Base de datos | SQL Server (esquema `mercpd`), ODBC Driver 17 |
| Servidor WSGI | Waitress 3.0.2 |
| Archivos estáticos | WhiteNoise 6.12.0 |
| Visualización | Chart.js (`vendor/chart.umd.js`) |
| Publicación temporal | Cloudflare Tunnel |

## Metodología MERC-PD

### Valor del Activo (VA) — Tríada CIA ponderada

VA = (C * 0.40) + (I * 0.35) + (D * 0.25)

Confidencialidad, Integridad y Disponibilidad se califican de 1 a 3. El peso de Confidencialidad (40%) refleja la prioridad regulatoria sobre datos financieros y personales.

### Cálculo del riesgo

IBase = Máximo(IOperativo, ISPDP_efectivo, IFinanciero/Legal)
IFinal = IBase * (VA / 3.0)
Riesgo = Probabilidad * IFinal


Si un activo tiene **VA >= 2.5**, se aplica un "factor suelo": el impacto de protección de datos (SPDP) se eleva automáticamente a su nivel más alto, sin importar que el impacto informado sea menor.

### Clasificación en 5 niveles

| Nivel | Puntaje | SLA de tratamiento | Aceptación permitida |
|---|---|---|---|
| Muy Bajo | 0.33 – 1.49 | 180 días | Sí |
| Bajo | 1.50 – 2.99 | 90 días | Sí |
| Medio | 3.00 – 4.99 | 30 días | Excepcional, con justificación |
| Alto | 5.00 – 7.49 | 15 días | No |
| Crítico | 7.50 – 9.00 | 7 días | No |

**Regla obligatoria:** no se puede aceptar un riesgo Alto o Crítico, ni un riesgo asociado a un activo con VA >= 2.5, sin controles compensatorios. Esta regla se valida tanto en Django como en SQL Server.

### Opciones de tratamiento

Mitigar, Transferir, Evitar o Aceptar — cada una con directrices técnicas específicas (cifrado AES-256, MFA, RBAC, WAF, SIEM/SOAR, seguros cibernéticos, tokenización, etc.) y un responsable de aprobación definido.

## Roles y permisos

| Módulo | Administrador | Arquitecto de Seguridad | Custodio de Activo | Auditor |
|---|:---:|:---:|:---:|:---:|
| Monitoreo General | ✅ | ✅ | ✅ (filtrado) | ✅ |
| Registro y Valoración de Activos | ✅ | ✅ | ❌ | ❌ |
| Identificación de Riesgos | ✅ | ✅ | ❌ | ❌ |
| Tratamiento de Riesgo | ✅ | ✅ | ❌ | ❌ |
| Comunicación y Reportes | ✅ | ✅ | ✅ (sus activos) | ✅ (lectura/CSV) |
| Bitácora de Auditoría | ✅ | ❌ | ❌ | ✅ |
| Registrar Usuario | ✅ | ❌ | ❌ | ❌ |

## Instalación y ejecución local

> ⚠️ Ajustar esta sección a los pasos reales de tu repositorio (los `.bat` incluidos usan una ruta absoluta local; revisa la línea `cd /d` antes de ejecutarlos en otro equipo).

1. Clonar el repositorio:
```bash
   git clone https://github.com/mateoenriquez/kushki_mercpd_project.git
   cd kushki_mercpd_project
```
2. Crear y activar un entorno virtual, e instalar dependencias:
```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
```
3. Configurar variables de entorno (`DJANGO_SECRET_KEY`, `DJANGO_DB_HOST`, `DJANGO_DEBUG`, etc.).
4. Ejecutar el script maestro T-SQL sobre una base limpia para crear tablas, vistas, procedimientos, triggers y datos de demostración.
5. Levantar el servidor:
```bash
   python manage.py collectstatic --noinput
   python manage.py runserver
```
6. Ingresar con una cuenta de prueba (ver tabla de credenciales en el manual de usuario del repositorio; no se publican aquí por seguridad).

## Estructura funcional

| Módulo | Endpoint / vista principal | Descripción |
|---|---|---|
| Autenticación | `vista_login`, `vista_logout` | Valida credenciales contra `mercpd.Usuarios`. |
| Activos | `api_activos_registrar` | Valida C/I/D (1-3), calcula el VA y registra el activo. |
| Riesgos | `api_riesgos_evaluar` | Cruza activo, amenaza y vulnerabilidad; calcula impacto y riesgo total. |
| Dashboard | `api_dashboard_datos`, `api_dashboard_kpis` | Matriz detallada, KPIs, MTTM, IRRP, SLA, matriz de calor. |
| Tratamientos | `api_tratamientos_registrar` | Aplica Mitigar/Transferir/Evitar/Aceptar y calcula riesgo residual. |
| Comunicación | `api_comunicaciones_registrar`, `api_reporte_csv` | Observaciones, recomendaciones y exportación a CSV. |
| Auditoría | `api_auditoria_lista` | Últimas 200 acciones registradas en el sistema. |

## Capturas de pantalla

> Login

<img width="854" height="453" alt="imagen" src="https://github.com/user-attachments/assets/d7676e38-55a2-4756-8584-a7340230d1d7" />

> Dashboard de Monitoreo General

<img width="860" height="463" alt="imagen" src="https://github.com/user-attachments/assets/e1c0f67b-e215-4ef0-b0c5-0fdecde84b92" />


> Registro de Activos

<img width="859" height="462" alt="imagen" src="https://github.com/user-attachments/assets/f9d7eb42-12ff-4e67-8b04-835f00104b0b" />


> Identificación de riesgos

<img width="863" height="463" alt="imagen" src="https://github.com/user-attachments/assets/71aba21a-1a42-476a-95e5-81cfdc8923aa" />


> Tratamiento

<img width="859" height="462" alt="imagen" src="https://github.com/user-attachments/assets/4dbbdabc-ace2-439d-8086-dd3034d34f9f" />


> Comunicacion

<img width="859" height="463" alt="imagen" src="https://github.com/user-attachments/assets/99a3f10c-6665-4f75-8028-aec1bc59118f" />


> Reporte CSV de acciones

<img width="862" height="321" alt="imagen" src="https://github.com/user-attachments/assets/4fff2e33-9810-457d-bfc9-400d8fcd0148" />


> Auditoría

<img width="857" height="459" alt="imagen" src="https://github.com/user-attachments/assets/e8d4f988-c1d3-4622-bd5d-0cc6a9a1b9b2" />


> Registrar Usuario 
<img width="857" height="461" alt="imagen" src="https://github.com/user-attachments/assets/f0f697ad-02ae-4a45-9a22-71ceeafac09e" />




## Casos de prueba

| Caso | Resultado esperado |
|---|---|
| Login con cuenta válida | Carga el dashboard y muestra rol en la barra lateral |
| Registrar activo con C=3, I=2, D=3 | VA calculado = 2.65 |
| Crear riesgo sobre activo con VA >= 2.5 | El sistema eleva automáticamente el impacto SPDP efectivo |
| Aplicar tratamiento "Mitigar" con eficacia 0.70 | Riesgo residual = Riesgo total * 0.30 |
| Intentar aceptar un riesgo Alto/Crítico | La aplicación rechaza la operación por regla MERC-PD |
| Registrar actividad y revisar auditoría | La bitácora refleja el evento CREAR correspondiente |

## Observaciones y deuda técnica conocida

- La vista SQL `mercpd.vw_KPIsRiesgo` todavía agrupa todo `RiesgoActual < 3.0` como "RiesgosBajo"; la lógica de 5 niveles sí está separada en Django, pero falta alinear esa vista si se consulta directamente desde SSMS.
- El script maestro contiene credenciales de demostración pensadas para entorno académico; deben cambiarse antes de cualquier despliegue fuera de ese contexto.
- `DEBUG` está desactivado por defecto y solo se activa vía `DJANGO_DEBUG=true`; `SECRET_KEY` se toma de variable de entorno.

## Integrantes

- Mateo Enríquez
- Alexander Valladares
- Carlos Moreta
- Steven Pacheco

**Asignatura:** Seguridad Informática (NRC 5485) — Universidad de Las Américas (UDLA)
