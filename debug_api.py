#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la conexión con Finnhub API
"""
import requests
import os
import json

def test_api_connection():
    # Obtener API key
    api_key = os.environ.get('FINNHUB_API_KEY', 'demo')

    print("=" * 60)
    print("DIAGNÓSTICO FINNHUB API")
    print("=" * 60)
    print(f"API Key configurada: {api_key[:10]}... (primeros 10 caracteres)")
    print(f"¿Usando demo token?: {'SÍ' if api_key == 'demo' else 'NO'}")
    print()

    # Test con GGAL
    print("Probando símbolo: GGAL")
    print("-" * 60)

    try:
        response = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={
                "symbol": "GGAL",
                "token": api_key
            },
            timeout=5
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()

        data = response.json()
        print(f"Response JSON:")
        print(json.dumps(data, indent=2))
        print()

        if "c" in data and data["c"] > 0:
            print("✅ ÉXITO: Datos recibidos correctamente")
            print(f"   Precio actual: ${data['c']}")
            print(f"   Cambio: {data.get('d', 0)} ({data.get('dp', 0)}%)")
        elif "c" in data and data["c"] == 0:
            print("⚠️  ADVERTENCIA: API devolvió precio = 0")
            print("   Posibles causas:")
            print("   - Mercado cerrado (verifica horario de mercado)")
            print("   - Símbolo no disponible con token demo")
            print("   - Rate limit excedido")
        else:
            print("❌ ERROR: Respuesta sin campo 'c' (precio)")
            print(f"   Datos recibidos: {data}")

    except requests.exceptions.Timeout:
        print("❌ ERROR: Timeout - La API no respondió en 5 segundos")
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se pudo conectar a la API")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")

    print()
    print("=" * 60)
    print("RECOMENDACIONES:")
    print("=" * 60)

    if api_key == "demo":
        print("1. Configura tu API key real:")
        print("   export FINNHUB_API_KEY='tu_api_key_aqui'")
        print("2. Obtén una API key gratis en: https://finnhub.io")
    else:
        print("1. Verifica que el mercado esté abierto (US market hours)")
        print("2. El mercado NYSE opera: Lun-Vie 9:30 AM - 4:00 PM ET")
        print("3. Fuera de horario, los datos pueden estar congelados")

    print()

if __name__ == "__main__":
    test_api_connection()
