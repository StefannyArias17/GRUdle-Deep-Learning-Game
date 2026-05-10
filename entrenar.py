#!/usr/bin/env python3
"""
Script de entrenamiento del modelo GRU.
Ejecuta: python entrenar.py
Opcional: python entrenar.py --colab (para Google Colab con GPU)
"""

import os
import sys
import argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main():
    parser = argparse.ArgumentParser(description="Entrenar modelos GRU para Duelo de Palabras")
    parser.add_argument("--epochs-cat1", type=int, default=40,
                        help="Épocas para Categoría 1 (default: 40)")
    parser.add_argument("--epochs-cat2", type=int, default=50,
                        help="Épocas para Categoría 2 (default: 50)")
    parser.add_argument("--batch", type=int, default=32,
                        help="Tamaño de batch (default: 32)")
    parser.add_argument("--colab", action="store_true",
                        help="Modo Google Colab (habilita GPU)")
    parser.add_argument("--quiet", action="store_true",
                        help="Modo silencioso")
    args = parser.parse_args()

    if args.colab:
        print("🚀 Modo Google Colab activado")
        try:
            import tensorflow as tf
            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                print(f"✅ GPU detectada: {gpus[0].name}")
            else:
                print("⚠️  Sin GPU detectada, usando CPU")
        except Exception:
            pass

    dataset_path = os.path.join(ROOT, "dataset", "palabras_es.json")
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset no encontrado: {dataset_path}")
        sys.exit(1)

    print(f"\n📊 Dataset: {dataset_path}")
    print(f"📈 Épocas Cat1: {args.epochs_cat1}")
    print(f"📈 Épocas Cat2: {args.epochs_cat2}")
    print(f"📦 Batch size: {args.batch}")
    print()

    from model.gru import entrenar
    resultados = entrenar(
        dataset_path,
        epochs_cat1=args.epochs_cat1,
        epochs_cat2=args.epochs_cat2,
        batch_size=args.batch,
        verbose=not args.quiet
    )

    print("\n📊 Resultados finales:")
    for key, val in resultados.items():
        print(f"  {key}: {val:.4f}")

    print("\n✅ Modelos guardados en: model/pesos/")
    print("🎮 Ahora puedes ejecutar: python main.py")


if __name__ == "__main__":
    main()
