#!/usr/bin/env python3
"""
Duelo de Palabras - Punto de entrada principal.
Ejecuta: python main.py
"""

import os
import sys

# Aseguramos que el directorio raíz esté en el path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def main():
    print("=" * 50)
    print("  ⚔  DUELO DE PALABRAS  ⚔")
    print("  Humano vs. Inteligencia Artificial")
    print("=" * 50)
    print()

    # Verificar dataset
    dataset_path = os.path.join(ROOT, "dataset", "palabras_es.json")
    if not os.path.exists(dataset_path):
        print("❌ Dataset no encontrado en:", dataset_path)
        sys.exit(1)
    print("✅ Dataset cargado")

    # Verificar modelos entrenados (opcional)
    modelo_path = os.path.join(ROOT, "model", "pesos", "gru_cat1.keras")
    if os.path.exists(modelo_path):
        print("✅ Modelos GRU encontrados")
    else:
        print("⚠️  Modelos GRU no entrenados. Usando modo heurístico.")
        print("   Para entrenar: python model/gru.py")
    print()

    # Lanzar GUI
    try:
        from gui.main_gui import App
        app = App()
        app.mainloop()
    except ImportError as e:
        print(f"❌ Error al iniciar la GUI: {e}")
        print("Asegúrate de tener tkinter instalado:")
        print("  sudo apt-get install python3-tk  (Linux)")
        sys.exit(1)


if __name__ == "__main__":
    main()
