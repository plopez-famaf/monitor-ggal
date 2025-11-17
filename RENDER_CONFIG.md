# Configuración de Variables de Entorno en Render.com

## Problema Actual

Tu app en Render está devolviendo status 202 constantemente porque **no tiene configurada la variable de entorno FINNHUB_API_KEY**.

El thread background está corriendo pero falla silenciosamente porque usa el token "demo" que ya no funciona (401 Unauthorized).

## Solución: Configurar Variable de Entorno

### Paso 1: Acceder al Dashboard de Render

1. Ve a: https://dashboard.render.com
2. Encuentra tu servicio "monitor-ggal"
3. Click en el nombre del servicio

### Paso 2: Agregar Variable de Entorno

1. En el menú lateral izquierdo, click en **"Environment"**
2. Busca la sección **"Environment Variables"**
3. Click en **"Add Environment Variable"**

### Paso 3: Configurar la Variable

Agrega:
- **Key**: `FINNHUB_API_KEY`
- **Value**: `d4db3o9r01qovljouiq0d4db3o9r01qovljouiqg`

### Paso 4: Guardar y Re-desplegar

1. Click en **"Save Changes"** (botón verde)
2. Render automáticamente re-desplegará tu app
3. Espera 1-2 minutos para que complete el re-despliegue

### Paso 5: Verificar que Funciona

Después del re-despliegue, verifica:

```bash
# 1. Verificar configuración (nuevo endpoint de debug)
curl https://monitor-ggal.onrender.com/api/debug | python -m json.tool

# Deberías ver:
# "api_key_configured": true,
# "api_key_is_demo": false,
# "test_connection": { "has_price": true, ... }

# 2. Esperar 30 segundos y verificar que hay datos
curl https://monitor-ggal.onrender.com/api/estadisticas | python -m json.tool

# Deberías ver precios en vez de {"error": "Sin datos"}
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
