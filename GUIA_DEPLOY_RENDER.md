# Guía Completa: Deploy Monitor GGAL en Render

## Paso 1: Preparar el proyecto localmente

### 1.1 Crear estructura de carpetas

```
proyecto-ggal/
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
├── .gitignore
└── README.md
```

### 1.2 Crear archivo `app.py`

```python
from flask import Flask, jsonify, render_template
import requests
import threading
import time
from datetime import datetime
from collections import deque
import os

app = Flask(__name__)

class MonitorGGAL:
    def __init__(self, api_key):
        self.api_key = api_key
        self.symbol = "GGAL"
        self.historial = deque(maxlen=1000)
        self.running = False
    
    def obtener_precio(self):
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={
                    "symbol": self.symbol,
                    "token": self.api_key
                },
                timeout=5
            )
            data = response.json()
            
            if "c" in data:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "price": data.get("c", 0),
                    "high": data.get("h", 0),
                    "low": data.get("l", 0),
                    "open": data.get("o", 0),
                    "change": round(data.get("c", 0) - data.get("pc", 0), 2),
                    "change_percent": round((data.get("c", 0) - data.get("pc", 0)) / data.get("pc", 1) * 100, 2)
                }
        except Exception as e:
            print(f"Error obteniendo precio: {e}")
        return None
    
    def monitorear_background(self, intervalo=10):
        self.running = True
        print(f"Iniciando monitoreo de {self.symbol}...")
        while self.running:
            precio = self.obtener_precio()
            if precio:
                self.historial.append(precio)
                print(f"[{precio['timestamp']}] Precio: ${precio['price']:.2f}")
            time.sleep(intervalo)
    
    def obtener_historial(self):
        return list(self.historial)

# Obtener API key desde variable de entorno
api_key = os.environ.get('FINNHUB_API_KEY')
if not api_key:
    print("ADVERTENCIA: FINNHUB_API_KEY no está configurada")
    api_key = "demo"

monitor = MonitorGGAL(api_key=api_key)

# Iniciar monitoreo en background thread
thread = threading.Thread(target=monitor.monitorear_background, args=(10,), daemon=True)
thread.start()

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/precio-actual')
def precio_actual():
    if monitor.historial:
        return jsonify(monitor.historial[-1])
    return jsonify({"error": "Sin datos", "message": "Esperando primer dato..."}), 202

@app.route('/api/historial')
def historial():
    return jsonify(monitor.obtener_historial())

@app.route('/api/estadisticas')
def estadisticas():
    if not monitor.historial:
        return jsonify({"error": "Sin datos"}), 202
    
    precios = [p["price"] for p in monitor.historial]
    return jsonify({
        "max": round(max(precios), 2),
        "min": round(min(precios), 2),
        "promedio": round(sum(precios) / len(precios), 2),
        "muestras": len(precios),
        "ultimo_update": monitor.historial[-1]["timestamp"]
    })

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "symbol": "GGAL"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
```

### 1.3 Crear archivo `requirements.txt`

```
Flask==3.0.0
requests==2.31.0
gunicorn==21.2.0
```

### 1.4 Crear archivo `.gitignore`

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.vscode/
.DS_Store
*.log
.env
```

### 1.5 Crear archivo `templates/index.html`

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor GGAL - Banco Galicia</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.15);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.2em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .precio-actual {
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            margin: 20px 0;
        }
        
        .cambio {
            font-size: 1.3em;
            margin: 10px 0;
            font-weight: 600;
        }
        
        .cambio.positivo {
            color: #27ae60;
        }
        
        .cambio.negativo {
            color: #e74c3c;
        }
        
        .timestamp {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-top: 15px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 20px;
        }
        
        .stat-item {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 0.85em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 8px;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .chart-container {
            position: relative;
            height: 350px;
            margin-top: 20px;
        }
        
        .loading {
            text-align: center;
            color: #7f8c8d;
            font-size: 1.1em;
            padding: 20px;
        }
        
        .error {
            background: #fadbd8;
            color: #c0392b;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #27ae60;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .info {
            background: #d6eaf8;
            color: #1a5276;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            h1 {
                font-size: 1.8em;
            }
            
            .precio-actual {
                font-size: 2em;
            }
            
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Monitor GGAL - Banco Galicia</h1>
        
        <div id="error-container"></div>
        
        <div class="grid">
            <div class="card">
                <h2><span class="status-indicator"></span>Precio Actual</h2>
                <div class="precio-actual" id="precioActual">
                    <span class="loading">Cargando...</span>
                </div>
                <div class="cambio" id="cambio">--</div>
                <div class="timestamp" id="timestamp">--</div>
            </div>
            
            <div class="card">
                <h2>Estadísticas</h2>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-label">Máximo</div>
                        <div class="stat-value" id="maximo">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Mínimo</div>
                        <div class="stat-value" id="minimo">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Promedio</div>
                        <div class="stat-value" id="promedio">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Muestras</div>
                        <div class="stat-value" id="muestras">--</div>
                    </div>
                </div>
            </div>
            
            <div class="card full-width">
                <h2>Gráfico de Precios</h2>
                <div class="chart-container">
                    <canvas id="grafico"></canvas>
                </div>
            </div>
            
            <div class="info full-width">
                <strong>ℹ️ Información:</strong> Los datos se actualizan cada 10 segundos desde la API de Finnhub. 
                Este monitor es para fines educativos. No es recomendación de inversión.
            </div>
        </div>
    </div>

    <script>
        let chart = null;
        let ultimaActualizacion = 0;
        
        async function actualizarDatos() {
            try {
                // Precio actual
                const respPrecio = await fetch('/api/precio-actual');
                
                if (respPrecio.status === 202) {
                    // Esperando datos
                    document.getElementById('precioActual').innerHTML = '<span class="loading">Esperando datos iniciales...</span>';
                    return;
                }
                
                if (!respPrecio.ok) throw new Error('Error al obtener precio');
                
                const precio = await respPrecio.json();
                
                // Limpiar error si existía
                document.getElementById('error-container').innerHTML = '';
                
                // Actualizar precio actual
                document.getElementById('precioActual').textContent = `$${precio.price.toFixed(2)}`;
                
                // Actualizar cambio
                const cambioVal = precio.change;
                const cambioPct = precio.change_percent;
                const cambioEl = document.getElementById('cambio');
                cambioEl.textContent = `${cambioVal > 0 ? '↗' : '↘'} ${Math.abs(cambioVal).toFixed(2)} (${cambioVal > 0 ? '+' : ''}${cambioPct.toFixed(2)}%)`;
                cambioEl.className = cambioVal > 0 ? 'cambio positivo' : 'cambio negativo';
                
                // Actualizar timestamp
                const fecha = new Date(precio.timestamp);
                document.getElementById('timestamp').textContent = `Actualizado: ${fecha.toLocaleTimeString('es-AR')}`;
                
                // Estadísticas
                const respStats = await fetch('/api/estadisticas');
                if (respStats.ok) {
                    const stats = await respStats.json();
                    
                    document.getElementById('maximo').textContent = `$${stats.max.toFixed(2)}`;
                    document.getElementById('minimo').textContent = `$${stats.min.toFixed(2)}`;
                    document.getElementById('promedio').textContent = `$${stats.promedio.toFixed(2)}`;
                    document.getElementById('muestras').textContent = stats.muestras;
                }
                
                // Historial para gráfico
                const respHistorial = await fetch('/api/historial');
                if (respHistorial.ok) {
                    const historial = await respHistorial.json();
                    if (historial.length > 0) {
                        actualizarGrafico(historial);
                    }
                }
                
            } catch (error) {
                console.error('Error:', error);
                const errorDiv = document.getElementById('error-container');
                errorDiv.innerHTML = `<div class="error">⚠️ Error: ${error.message}</div>`;
            }
        }

        function actualizarGrafico(datos) {
            const ctx = document.getElementById('grafico').getContext('2d');
            const labels = datos.map(d => {
                const fecha = new Date(d.timestamp);
                return fecha.toLocaleTimeString('es-AR', { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit'
                });
            });
            const precios = datos.map(d => d.price);
            
            if (chart) {
                chart.data.labels = labels;
                chart.data.datasets[0].data = precios;
                chart.update('none');
            } else {
                chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Precio GGAL (USD)',
                            data: precios,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 4,
                            pointBackgroundColor: '#667eea',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointHoverRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                labels: {
                                    font: { size: 12 },
                                    usePointStyle: true,
                                    padding: 15
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(0,0,0,0.8)',
                                padding: 12,
                                titleFont: { size: 13 },
                                bodyFont: { size: 12 },
                                callbacks: {
                                    label: function(context) {
                                        return `$${context.parsed.y.toFixed(2)}`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                grid: { color: 'rgba(0,0,0,0.05)' },
                                ticks: { callback: function(value) { return '$' + value.toFixed(2); } }
                            },
                            x: {
                                grid: { color: 'rgba(0,0,0,0.05)' }
                            }
                        }
                    }
                });
            }
        }

        // Actualizar datos inicialmente y cada 10 segundos
        actualizarDatos();
        setInterval(actualizarDatos, 10000);
    </script>
</body>
</html>
```

### 1.6 Crear archivo `README.md`

```markdown
# Monitor GGAL - Banco Galicia

Monitor en tiempo real del precio del ADR de Banco Galicia (GGAL) usando la API de Finnhub.

## Características

- Actualización de precios cada 10 segundos
- Gráfico interactivo de precios
- Estadísticas en tiempo real (máximo, mínimo, promedio)
- Interfaz web responsive
- Deploy automático en Render

## Requisitos Locales

- Python 3.9+
- pip

## Instalación Local

```bash
# Clonar repositorio
git clone https://github.com/tuusuario/monitor-ggal.git
cd monitor-ggal

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar API key
export FINNHUB_API_KEY="tu_api_key_aqui"  # En Windows: set FINNHUB_API_KEY=...

# Ejecutar
python app.py
```

Luego acceder a `http://localhost:5000`

## Deploy en Render

Ver GUIA_DEPLOY_RENDER.md

## API Endpoints

- `GET /` - Página principal
- `GET /api/precio-actual` - Último precio
- `GET /api/historial` - Historial completo
- `GET /api/estadisticas` - Estadísticas
- `GET /api/health` - Health check

## Notas

- Requiere API key gratis de Finnhub (https://finnhub.io)
- No es recomendación de inversión
- Fines educativos
```

## Paso 2: Preparar Git y GitHub

### 2.1 Inicializar repositorio Git

```bash
# En la carpeta del proyecto
git init
git add .
git commit -m "Initial commit: Monitor GGAL"
```

### 2.2 Crear repositorio en GitHub

1. Ir a https://github.com/new
2. Nombre del repositorio: `monitor-ggal`
3. Descripción: "Monitor en tiempo real de GGAL - Banco Galicia"
4. Seleccionar "Public"
5. Click en "Create repository"

### 2.3 Conectar repositorio local con GitHub

```bash
git remote add origin https://github.com/TU_USUARIO/monitor-ggal.git
git branch -M main
git push -u origin main
```

## Paso 3: Obtener API Key de Finnhub

### 3.1 Registrarse

1. Ir a https://finnhub.io/
2. Click en "Sign Up" o "Get Free API Key"
3. Usar email y crear contraseña
4. Confirmar email

### 3.2 Obtener la API Key

1. Login en tu cuenta
2. Ir a Dashboard
3. Copiar tu API Key (visible al principio)
4. Guardarla en lugar seguro (la usaremos en Render)

**Nota:** El plan gratuito incluye:
- 60 solicitudes/minuto
- Datos en tiempo real
- Suficiente para nuestro monitor

## Paso 4: Crear cuenta en Render

### 4.1 Registrarse

1. Ir a https://render.com
2. Click en "Get Started"
3. Seleccionar "Sign Up with GitHub"
4. Autorizar Render a acceder a GitHub

### 4.2 Conectar repositorio

1. Una vez en el dashboard de Render, click en "New +"
2. Seleccionar "Web Service"
3. Click en "Connect a repository"
4. Buscar `monitor-ggal`
5. Seleccionar el repositorio
6. Click en "Connect"

## Paso 5: Configurar el servicio en Render

### 5.1 Configuración básica

En la siguiente pantalla, completar:

**Name:** `monitor-ggal` (nombre del servicio)

**Environment:** `Python 3` (debería estar auto-seleccionado)

**Build Command:** Dejar en blanco (usa valores por defecto)

**Start Command:** 
```
gunicorn app:app
```

### 5.2 Plan

Seleccionar "Free" (abajo a la izquierda)

**Nota:** En plan Free:
- El servicio se suspende después de 15 minutos sin actividad
- Se reinicia cuando recibe una solicitud
- Perfecto para monitoreo con actualizaciones periódicas

### 5.3 Variables de entorno

1. Bajar hasta la sección "Environment"
2. Click en "Add Environment Variable"
3. Agregar:
   - **Key:** `FINNHUB_API_KEY`
   - **Value:** `tu_api_key_aqui` (pegar la API key de Finnhub)
4. Click en "Save"

## Paso 6: Deployar

### 6.1 Iniciar deploy

1. Una vez configurado todo, Render automáticamente iniciará el deploy
2. En "Events" verás el progreso
3. Esperar a que complete (típicamente 2-3 minutos)

### 6.2 Verificar deploy exitoso

1. Cuando complete, verás "Your service is live"
2. El URL será algo como: `https://monitor-ggal.onrender.com`
3. Click en el URL para acceder a tu monitor

## Paso 7: Probar la aplicación

### 7.1 Acceder

```
https://monitor-ggal.onrender.com
```

### 7.2 Verificar que funciona

- Debería cargar la página en unos segundos
- El gráfico comenzará a actualizarse
- Esperar 2-3 actualizaciones (20-30 segundos) para ver datos

### 7.3 Si no funciona

1. En Render, ir a "Logs"
2. Ver si hay errores
3. Verificar que `FINNHUB_API_KEY` está correcta
4. Click en "Manual Deploy" > "Deploy latest" para reintentar

## Paso 8: Mantener en funcionamiento

### 8.1 Problema: El servicio se suspende

En plan Free, el servicio se suspende tras 15 minutos sin actividad. Soluciones:

**Opción A: Monitoreo externo (Recomendado)**

Usar un servicio gratuito para hacer ping cada 10 minutos:

1. Ir a https://uptimerobot.com
2. Sign Up gratis
3. Add New Monitor
   - Monitor Type: `HTTP(s)`
   - URL: `https://monitor-ggal.onrender.com/api/health`
   - Monitoring Interval: `5 minutes`
4. Click "Create Monitor"

Esto mantiene tu servicio activo sin costo.

**Opción B: Upgrade a plan de pago**

Si necesitas disponibilidad 24/7, Render ofrece plans pagos a partir de $7/mes.

### 8.2 Actualizar código

Si haces cambios locales:

```bash
# En tu computadora
git add .
git commit -m "Descripción del cambio"
git push origin main
```

Render automáticamente detecta cambios en GitHub y redeploya.

### 8.3 Monitorear logs

En Render Dashboard:
1. Seleccionar tu servicio
2. Click en "Logs"
3. Ver en tiempo real lo que sucede

## Paso 9: Personalizaciones (Opcional)

### 9.1 Cambiar símbolo a monitorear

En `app.py`, línea 10:
```python
self.symbol = "GGAL"  # Cambiar aquí
```

Ejemplos: `AAPL`, `GOOGL`, `MSFT`, `TSLA`, etc.

### 9.2 Cambiar intervalo de actualización

En `app.py`, línea 73:
```python
thread = threading.Thread(target=monitor.monitorear_background, args=(10,), daemon=True)
# Cambiar 10 al intervalo en segundos que prefieras
```

### 9.3 Agregar más símbolos

Modificar la clase `MonitorGGAL` para soportar múltiples símbolos:

```python
class MonitorGGAL:
    def __init__(self, api_key, simbolos=["GGAL"]):
        self.api_key = api_key
        self.simbolos = simbolos
        self.historial = {sym: deque(maxlen=1000) for sym in simbolos}
        # ...
```

## Troubleshooting

### Problema: "Error 404 Not Found"

**Solución:** 
- El servicio está suspendido (plan Free)
- Esperar a que Render lo despierte
- O usar Uptime Robot como se describe en Paso 8.1

### Problema: "FINNHUB_API_KEY no está configurada"

**Solución:**
1. Ir a Render Dashboard
2. Seleccionar servicio
3. Click en "Environment"
4. Verificar que `FINNHUB_API_KEY` está presente
5. Click en "Manual Deploy" > "Deploy latest"

### Problema: Gráfico no se actualiza

**Solución:**
1. Verificar consola del navegador (F12 > Console)
2. Ver si hay errores CORS
3. En Render Logs, ver errores de backend

### Problema: Los datos se ven retrasados

**Solución:**
- Es normal. Finnhub tiene límite de 60 llamadas/minuto
- Con intervalo de 10 segundos, haces 6 llamadas/minuto (está bien)
- Si aumentas la frecuencia, podrías topar el límite

## Próximos pasos

1. **Alertas por Email**: Agregar notificaciones cuando el precio suba/baje X%
2. **Base de datos**: Guardar datos en Postgres para análisis histórico
3. **Mobile App**: Crear app móvil que consulte tu backend
4. **Múltiples símbolos**: Monitorear varios stocks simultáneamente
5. **Predicción**: Agregar ML para predecir movimientos

## Soporte

Si tienes problemas:

1. Revisar Logs en Render Dashboard
2. Verificar https://status.render.com
3. Contactar a Render: support@render.com
4. Contactar a Finnhub: support@finnhub.io

## Licencia

MIT

## Disclaimer

Este proyecto es solo para fines educativos. No es recomendación de inversión. 
Consulta a un asesor financiero profesional antes de tomar decisiones de inversión.
```

## Resumen de archivos a crear

| Archivo | Ubicación |
|---------|-----------|
| app.py | Raíz del proyecto |
| requirements.txt | Raíz del proyecto |
| .gitignore | Raíz del proyecto |
| README.md | Raíz del proyecto |
| index.html | templates/ |

## Checklist final

- [ ] Crear carpeta del proyecto
- [ ] Crear todos los archivos listados arriba
- [ ] Hacer commit inicial en Git
- [ ] Subir a GitHub
- [ ] Crear cuenta en Render
- [ ] Conectar GitHub a Render
- [ ] Configurar `FINNHUB_API_KEY` en Render
- [ ] Deploy
- [ ] Verificar que funciona
- [ ] (Opcional) Configurar Uptime Robot

¡Listo! Tu monitor estará online.
