# test_ai.py
from src.ai_coach import ask_ai_coach

# 1. Creamos un diccionario con datos simulados de entrenamiento
sample_data = {
    "weekly_km": 38.5,
    "avg_pace": "5:12",
    "zone_distribution": {"Z1/Z2": "75%", "Z3": "15%", "Z4/Z5": "10%"}
}

print("🚀 Conectando con Gemini y enviando métricas de prueba...")

# 2. Llamamos a la función que creamos en src/ai_coach.py
respuesta = ask_ai_coach(sample_data)

# 3. Imprimimos el resultado directo en la consola
print("\n--- 🤖 RESPUESTA DEL ENTRENADOR VIRTUAL ---")
print(respuesta)
print("------------------------------------------")