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