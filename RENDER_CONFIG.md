# Configuración Completa de Render.com

## Problemas Actuales

Tu app en Render tiene 2 problemas:

1. **Gunicorn con múltiples workers** - No usa el Procfile, crea workers separados
2. **Puede faltar FINNHUB_API_KEY** - Verifica que esté configurada

### ¿Por qué múltiples workers es un problema?

El background thread colecta datos en UN worker, pero los requests HTTP van a OTROS workers que tienen `historial` vacío. Necesitas forzar `--workers=1`.

## Solución: Configurar Render Correctamente

### Paso 1: Acceder al Dashboard

1. Ve a: https://dashboard.render.com
2. Encuentra tu servicio "monitor-ggal"
3. Click en el nombre del servicio

### Paso 2: Configurar Start Command (CRÍTICO)

1. En el menú lateral, click en **"Settings"**
2. Busca la sección **"Build & Deploy"**
3. Encuentra el campo **"Start Command"**
4. **Cambia** de `gunicorn app:app` a:
   ```
   gunicorn --workers=1 --threads=2 --timeout=120 app:app
   ```
5. Click **"Save Changes"**

**IMPORTANTE:** Esto sobrescribe el Procfile. Render no usa Procfile automáticamente para Web Services.

### Paso 3: Configurar Variable de Entorno

1. En el menú lateral, click en **"Environment"**
2. Busca **"Environment Variables"**
3. Verifica que existe `FINNHUB_API_KEY`
4. Si NO existe, click **"Add Environment Variable"**:
   - **Key**: `FINNHUB_API_KEY`
   - **Value**: `d4db3o9r01qovljouiq0d4db3o9r01qovljouiqg`
5. Click **"Save Changes"**

### Paso 4: Re-desplegar Manualmente

1. Ve a la pestaña **"Manual Deploy"** (arriba)
2. Click **"Deploy latest commit"**
3. Espera 2-3 minutos para el re-despliegue

### Paso 5: Verificar que Funciona

Después del re-despliegue, verifica en los **Logs**:

**Deberías ver:**
```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: sync
[INFO] Booting worker with pid: XX        ← SOLO UN worker
Iniciando monitoreo de GGAL...
[timestamp] Precio: $XX.XX                ← Precios apareciendo
[timestamp] Precio: $XX.XX
```

**NO deberías ver:**
```
[INFO] Booting worker with pid: 65
[INFO] Booting worker with pid: 66        ← Múltiples workers = MAL
```

**Luego prueba los endpoints:**

```bash
# 1. Debug endpoint - verifica configuración
curl https://monitor-ggal.onrender.com/api/debug | python -m json.tool

# Debe mostrar:
# "historial_size": > 0           ← Número mayor a cero
# "api_key_is_demo": false
# "test_connection": {"has_price": true}

# 2. Precio actual - espera 30-60 segundos después del deploy
curl https://monitor-ggal.onrender.com/api/precio-actual | python -m json.tool

# Debe mostrar precio en vez de status 202
```

## Captura de Pantalla de Referencia

La sección de Environment Variables se ve así:

```
Environment Variables
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[+] Add Environment Variable

Key                    Value                                      [Actions]
─────────────────────────────────────────────────────────────────────────
FINNHUB_API_KEY       d4db3o9r01qovljouiq0d4db3o9r01qovljouiqg  [Edit] [Delete]
PORT                  5001                                        [Edit] [Delete]

                                            [Save Changes]
```

## Troubleshooting

### Si después de configurar sigue sin funcionar:

1. **Verifica los logs** (pestaña "Logs" en Render):
   - Busca: "Iniciando monitoreo de GGAL..."
   - NO deberías ver: "ADVERTENCIA: FINNHUB_API_KEY no está configurada"
   - Deberías ver: "[timestamp] Precio: $XX.XX"

2. **Verifica el mercado está abierto**:
   - NYSE opera: Lun-Vie 9:30 AM - 4:00 PM Eastern Time
   - Fuera de horario, los precios estarán congelados pero el endpoint funcionará

3. **Usa el endpoint de debug**:
   ```bash
   curl https://monitor-ggal.onrender.com/api/debug
   ```
   Esto te dirá exactamente qué está pasando.

## Variables de Entorno Recomendadas

Para un setup completo, configura:

| Variable | Valor | Requerida | Descripción |
|----------|-------|-----------|-------------|
| `FINNHUB_API_KEY` | `tu_api_key` | **Sí** | API key de Finnhub |
| `PORT` | `5001` | No | Puerto del servidor (Render lo configura automáticamente) |

## Nota de Seguridad

✅ Es seguro poner la API key en Render porque:
- Render encripta las variables de entorno
- No se muestran en los logs públicos
- Solo son accesibles por tu servicio

❌ NUNCA hagas commit de la API key en el código:
- No la pongas en `app.py` directamente
- No la subas a GitHub
- Siempre usa variables de entorno
