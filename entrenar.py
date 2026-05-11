#!/usr/bin/env python3
"""
Script de entrenamiento — Duelo de Palabras
==========================================
Entrena DOS modelos completamente independientes:

  Nivel 1 — GRU Secuencial Puro
    Arquitectura : Embedding → GRU(128) → Dense → Softmax
    Datos        : prefijo revelado de izquierda a derecha (G____, GA___, etc.)
    Sin pistas   : la IA NO recibe colores de intentos anteriores
    Guardado en  : model/pesos/gru_nivel1.keras

  Nivel 2 — MLP con Feedback Completo (Wordle)
    Arquitectura : Dense(512) → Dense(256) → Dense(128) → Softmax
    Datos        : estado acumulado de pistas (verdes/grises/azules/descartadas)
    Sin revelado : el tablero empieza vacío; la IA aprende de sus propios errores
    Guardado en  : model/pesos/mlp_nivel2.keras

Uso:
  python entrenar.py                         # defaults razonables
  python entrenar.py --epochs-n1 80 --epochs-n2 100
  python entrenar.py --colab                 # habilita GPU en Google Colab
  python entrenar.py --solo-n1               # solo entrenar nivel 1
  python entrenar.py --solo-n2               # solo entrenar nivel 2
"""

import os
import sys
import argparse
import json
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main():
    parser = argparse.ArgumentParser(
        description="Entrenar modelos de IA para Duelo de Palabras",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--epochs-n1", type=int, default=50,
                        help="Épocas para Nivel 1 GRU (default: 50)")
    parser.add_argument("--epochs-n2", type=int, default=60,
                        help="Épocas para Nivel 2 MLP (default: 60)")
    parser.add_argument("--batch", type=int, default=32,
                        help="Tamaño de batch (default: 32)")
    parser.add_argument("--colab", action="store_true",
                        help="Modo Google Colab — habilita GPU y ajusta paths")
    parser.add_argument("--solo-n1", action="store_true",
                        help="Entrenar solo el modelo de Nivel 1")
    parser.add_argument("--solo-n2", action="store_true",
                        help="Entrenar solo el modelo de Nivel 2")
    parser.add_argument("--quiet", action="store_true",
                        help="Modo silencioso (menos output)")
    args = parser.parse_args()

    if args.colab:
        print("🚀 Modo Google Colab activado")
        try:
            import tensorflow as tf
            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                tf.config.experimental.set_memory_growth(gpus[0], True)
                print(f"  ✅ GPU detectada: {gpus[0].name}")
            else:
                print("  ⚠️  Sin GPU. Usando CPU.")
        except Exception as e:
            print(f"  ⚠️  {e}")

    dataset_path = os.path.join(ROOT, "dataset", "palabras_es.json")
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset no encontrado: {dataset_path}")
        sys.exit(1)

    print("\n" + "═"*60)
    print("  DUELO DE PALABRAS — Entrenamiento de Modelos de IA")
    print("═"*60)
    print(f"  Dataset  : {dataset_path}")
    print(f"  Nivel 1  : GRU Secuencial — {args.epochs_n1} épocas")
    print(f"  Nivel 2  : MLP Wordle    — {args.epochs_n2} épocas")
    print(f"  Batch    : {args.batch}")
    print("═"*60 + "\n")

    from model.gru import (
        entrenar, generar_datos_nivel1, generar_datos_nivel2,
        construir_modelo_nivel1, construir_modelo_nivel2,
        MODELO_N1, MODELO_N2, VOCAB_N1, VOCAB_N2, MODELO_DIR, _norm
    )

    os.makedirs(MODELO_DIR, exist_ok=True)

    with open(dataset_path, 'r', encoding='utf-8') as f:
        ds = json.load(f)

    vocab = []
    for cat in ds["categorias"].values():
        for p in cat["palabras"]:
            vocab.append(_norm(p["palabra"]))
    vocab = sorted(set(p for p in vocab if 4 <= len(p) <= 10 and p.isalpha()))
    print(f"  Vocabulario total: {len(vocab)} palabras\n")

    resultados = {}

    try:
        import tensorflow as tf
    except ImportError:
        print("❌ TensorFlow no instalado. Ejecuta: pip install tensorflow")
        sys.exit(1)

    # ── NIVEL 1 ──────────────────────────────────────────────────────────────
    if not args.solo_n2:
        print("📘 NIVEL 1 — GRU Secuencial Puro")
        print("   Genera patrones de revelación de izquierda a derecha...")
        with open(VOCAB_N1, 'w', encoding='utf-8') as f:
            json.dump(vocab, f, ensure_ascii=False)

        X1, y1 = generar_datos_nivel1(vocab)
        print(f"   Muestras: {len(X1)}")
        idx = np.random.permutation(len(X1))
        X1, y1 = X1[idx], y1[idx]

        m1 = construir_modelo_nivel1(len(vocab))
        if m1:
            if not args.quiet: m1.summary()
            cb1 = [
                tf.keras.callbacks.EarlyStopping(
                    monitor='val_accuracy', patience=8,
                    restore_best_weights=True, verbose=1),
                tf.keras.callbacks.ReduceLROnPlateau(
                    monitor='val_loss', factor=0.5, patience=4, verbose=1),
                tf.keras.callbacks.ModelCheckpoint(
                    MODELO_N1, monitor='val_accuracy',
                    save_best_only=True, verbose=0)
            ]
            h1 = m1.fit(X1, y1,
                        epochs=args.epochs_n1, batch_size=args.batch,
                        validation_split=0.1, callbacks=cb1,
                        verbose=0 if args.quiet else 1)
            resultados["n1_acc"] = float(h1.history["accuracy"][-1])
            print(f"\n   ✅ Nivel 1 guardado. Accuracy: {resultados['n1_acc']:.3f}\n")

    # ── NIVEL 2 ──────────────────────────────────────────────────────────────
    if not args.solo_n1:
        print("📙 NIVEL 2 — MLP con Feedback Completo (Wordle)")
        print("   Simula partidas Wordle con verdes/grises/azules/descartadas...")
        with open(VOCAB_N2, 'w', encoding='utf-8') as f:
            json.dump(vocab, f, ensure_ascii=False)

        X2, y2 = generar_datos_nivel2(vocab, muestras_por_palabra=15)
        print(f"   Muestras: {len(X2)}")
        idx = np.random.permutation(len(y2))
        X2, y2 = X2[idx], y2[idx]

        input_dim = X2.shape[1]
        with open(os.path.join(MODELO_DIR, "meta_nivel2.json"), 'w') as f:
            json.dump({"input_dim": input_dim, "max_longitud": 10}, f)

        m2 = construir_modelo_nivel2(input_dim, len(vocab))
        if m2:
            if not args.quiet: m2.summary()
            cb2 = [
                tf.keras.callbacks.EarlyStopping(
                    monitor='val_accuracy', patience=10,
                    restore_best_weights=True, verbose=1),
                tf.keras.callbacks.ReduceLROnPlateau(
                    monitor='val_loss', factor=0.5, patience=5, verbose=1),
                tf.keras.callbacks.ModelCheckpoint(
                    MODELO_N2, monitor='val_accuracy',
                    save_best_only=True, verbose=0)
            ]
            h2 = m2.fit(X2, y2,
                        epochs=args.epochs_n2, batch_size=args.batch,
                        validation_split=0.1, callbacks=cb2,
                        verbose=0 if args.quiet else 1)
            resultados["n2_acc"] = float(h2.history["accuracy"][-1])
            print(f"\n   ✅ Nivel 2 guardado. Accuracy: {resultados['n2_acc']:.3f}\n")

    print("═"*60)
    print("  Resultados finales:")
    for k, v in resultados.items():
        print(f"    {k}: {v:.4f}")
    print("\n  Modelos guardados en: model/pesos/")
    print("  ▶  Ejecuta: python main.py")
    print("═"*60)


if __name__ == "__main__":
    main()