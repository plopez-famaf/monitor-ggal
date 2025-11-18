# Sistema de Validación de Predicciones

## ¿Cómo funciona?

El sistema **automáticamente** guarda cada predicción a 5 minutos y luego las valida contra los precios reales cuando el tiempo pasa.

### Flujo completo

```
1. Usuario pide forecast → GET /api/forecast
   ↓
2. Sistema genera predicción Kalman Filter
   Predicción: "En 5 min, precio será $10.73"
   ↓
3. Sistema GUARDA la predicción en PredictionTracker
   {
     timestamp: "2025-11-17T10:00:00",
     current_price: 10.50,
     predicted_price: 10.73,
     horizon_minutes: 5
   }
   ↓
4. Espera 5 minutos... ⏳
   ↓
5. Al próximo request, sistema VALIDA automáticamente
   - Busca precio real a las 10:05:00
   - Compara predicción vs realidad
   - Calcula error y métricas
   ↓
6. Resultados disponibles en GET /api/prediction-metrics
```

---

## API Endpoint: `/api/prediction-metrics`

### Respuesta de ejemplo

```json
{
  "metrics": {
    "total_predictions": 45,
    "validated_predictions": 32,
    "metrics": {
      "mae": 0.123,              // Mean Absolute Error ($)
      "rmse": 0.187,             // Root Mean Squared Error ($)
      "mape": 1.15,              // Mean Absolute Percentage Error (%)
      "directional_accuracy": 72.5,  // % predicciones correctas de dirección
      "interval_coverage": 94.2,     // % dentro del intervalo de confianza 95%
      "recent_mape": 0.98        // Error promedio últimas 10 predicciones
    },
    "summary": "Good: Reliable predictions"
  },
  "recent_predictions": [
    {
      "timestamp": "2025-11-17T10:00:00",
      "current_price": 10.50,
      "predicted_price": 10.73,
      "actual_price": 10.68,     // ← Precio real después de 5 min
      "error": -0.05,            // ← Diferencia (real - predicción)
      "error_pct": -0.48,        // ← Error porcentual
      "within_interval": true,   // ← ¿Cayó dentro del intervalo 95%?
      "horizon_minutes": 5
    }
    // ... más predicciones
  ]
}
```

---

## Métricas explicadas

### 1. **MAE (Mean Absolute Error)**
- Error promedio en dólares
- **Valor ideal**: < 0.10 (error de 10 centavos)
- **Ejemplo**: MAE = 0.123 → En promedio nos equivocamos por $0.12

### 2. **RMSE (Root Mean Squared Error)**
- Similar a MAE pero penaliza más los errores grandes
- **Valor ideal**: < 0.15
- **Ejemplo**: RMSE = 0.187 → Algunos errores grandes están presentes

### 3. **MAPE (Mean Absolute Percentage Error)**
- Error promedio en porcentaje
- **Valor ideal**: < 1.5%
- **Ejemplo**: MAPE = 1.15% → Nos equivocamos por ~1% en promedio

### 4. **Directional Accuracy**
- % de veces que predijimos la dirección correcta (sube/baja)
- **Valor ideal**: > 60%
- **Ejemplo**: 72.5% → De 100 predicciones, 72 acertaron la dirección

### 5. **Interval Coverage**
- % de precios reales que cayeron dentro del intervalo de confianza 95%
- **Valor ideal**: ~95% (teóricamente debería ser 95%)
- **Ejemplo**: 94.2% → Casi perfecto, el intervalo está bien calibrado

### 6. **Recent MAPE**
- Error de las últimas 10 predicciones
- Detecta si el modelo está mejorando o empeorando
- **Ejemplo**: recent_mape = 0.98% → Últimas predicciones muy buenas

---

## Interpretación de Resultados

### ✅ Excelente rendimiento
```
Directional Accuracy: > 70%
MAPE: < 1.0%
Interval Coverage: 93-97%
Summary: "Excellent: High accuracy, low error"
```

### ✔️ Buen rendimiento
```
Directional Accuracy: 60-70%
MAPE: 1.0-1.5%
Interval Coverage: 90-95%
Summary: "Good: Reliable predictions"
```

### ⚠️ Rendimiento aceptable
```
Directional Accuracy: 50-60%
MAPE: 1.5-2.5%
Interval Coverage: 85-92%
Summary: "Fair: Moderate accuracy"
```

### ❌ Mal rendimiento
```
Directional Accuracy: < 50%
MAPE: > 2.5%
Interval Coverage: < 85%
Summary: "Poor: Needs parameter tuning"
```

**Si ves mal rendimiento**: Ajusta los parámetros del Kalman Filter:
- Aumenta `process_noise` si el mercado es muy volátil
- Reduce `measurement_noise` si los precios son muy precisos

---

## Casos de uso

### 1. Verificar si el modelo funciona bien

```bash
curl http://localhost:5001/api/prediction-metrics

# Ver directional_accuracy
# Si > 60% → El modelo está funcionando
# Si < 50% → Algo está mal (peor que azar)
```

### 2. Comparar antes/después de ajustar parámetros

```python
# Configuración A: process_noise=0.01
# Esperar 1 hora, consultar métricas
# → MAPE = 1.5%

# Configuración B: process_noise=0.05
# Esperar 1 hora, consultar métricas
# → MAPE = 1.1%  ← ¡Mejor!
```

### 3. Detectar si el mercado cambió

```bash
# Si recent_mape >> mape
# → Últimas predicciones peores que promedio histórico
# → El mercado cambió de comportamiento
# → Tal vez ajustar parámetros
```

---

## Almacenamiento

- **Máximo**: 100 predicciones en memoria
- **Validación**: Automática cada vez que se pide `/api/forecast`
- **Limpieza**: Predicciones viejas se eliminan después de 24 horas

Para aumentar el límite, editar en `app.py`:

```python
prediction_tracker = PredictionTracker(max_predictions=500)  # ← Cambiar aquí
```

---

## Debugging

### Ver validaciones en tiempo real

Los logs muestran cuando se validan predicciones:

```
✅ Validated 3 prediction(s)
```

### Ver detalles de una predicción

```bash
curl http://localhost:5001/api/prediction-metrics | jq '.recent_predictions[0]'
```

Output:
```json
{
  "timestamp": "2025-11-17T10:00:00",
  "current_price": 10.50,
  "predicted_price": 10.73,
  "actual_price": 10.68,
  "error": -0.05,
  "error_pct": -0.48,
  "velocity": 0.0462,
  "uncertainty": 0.112,
  "confidence": "medium",
  "lower_bound": 10.51,
  "upper_bound": 10.95,
  "within_interval": true,
  "validated": true,
  "validation_time": "2025-11-17T10:05:03"
}
```

---

## Ejemplo de análisis completo

### Escenario: Predicción perfecta

```json
{
  "predicted_price": 10.73,
  "actual_price": 10.73,
  "error": 0.00,           // ← Error cero!
  "error_pct": 0.00,
  "within_interval": true
}
```

### Escenario: Buena predicción

```json
{
  "predicted_price": 10.73,
  "actual_price": 10.68,
  "error": -0.05,          // ← Pequeño error
  "error_pct": -0.48,      // ← Menos de 1%
  "within_interval": true  // ← Dentro del intervalo
}
```

### Escenario: Mala predicción

```json
{
  "predicted_price": 10.73,
  "actual_price": 10.45,
  "error": -0.28,          // ← Error grande
  "error_pct": -2.67,      // ← >2%
  "within_interval": false // ← Fuera del intervalo!
}
```

---

## Limitaciones

1. **Requiere 5 minutos**: No puedes ver métricas inmediatamente, necesitas esperar que las predicciones se validen
2. **Solo 5min horizon**: Solo valida predicciones a 5 minutos (las de 1min y 10min no se guardan)
3. **In-memory**: Se pierde todo al reiniciar la app
4. **Tolerancia**: Busca precio real ±30 segundos del tiempo exacto

---

## Próximas mejoras posibles

1. **Persistencia**: Guardar predicciones en base de datos
2. **Múltiples horizontes**: Validar también 1min y 10min
3. **Visualización**: Gráfico de error vs tiempo
4. **Alertas**: Notificar si MAPE > 3% (modelo degradándose)
5. **A/B Testing**: Comparar diferentes parámetros del Kalman Filter

---

## Resumen ejecutivo

**¿Para qué sirve?**
- Saber si el Kalman Filter está funcionando bien
- Decidir si necesitas ajustar parámetros
- Tener confianza en las predicciones antes de usarlas para trading

**¿Cómo usarlo?**
1. Deja la app corriendo por 1 hora
2. Consulta `/api/prediction-metrics`
3. Mira `directional_accuracy` y `mape`
4. Si están bien → confía en las predicciones
5. Si están mal → ajusta `process_noise` y `measurement_noise`
