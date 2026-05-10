"""
Arquitectura GRU para el agente de Duelo de Palabras.
Implementa dos modos:
  - Categoría 1: GRU secuencial puro (solo letras reveladas)
  - Categoría 2: Multi-input GRU (letras reveladas + vector de pistas)
"""

import os
import json
import random
import numpy as np
from typing import List, Tuple, Dict, Optional

# ─── Constantes de tokenización ────────────────────────────────────────────────
PAD    = 0
LETRAS = "abcdefghijklmnopqrstuvwxyz"
CHAR_A_IDX = {c: i + 1 for i, c in enumerate(LETRAS)}
IDX_A_CHAR = {v: k for k, v in CHAR_A_IDX.items()}
VOCAB_SIZE  = 27
ALPHA_SIZE  = 26
MAX_LEN     = 6

MODELO_DIR   = os.path.join(os.path.dirname(__file__), "pesos")
MODELO_CAT1  = os.path.join(MODELO_DIR, "gru_cat1.keras")
MODELO_CAT2  = os.path.join(MODELO_DIR, "gru_cat2.keras")
VOCAB_PATH   = os.path.join(MODELO_DIR, "vocabulario.json")


def palabra_a_vector(patron: str) -> List[int]:
    vec = []
    for c in patron.lower():
        if c == '_' or c == ' ':
            vec.append(PAD)
        else:
            vec.append(CHAR_A_IDX.get(c, PAD))
    while len(vec) < MAX_LEN:
        vec.append(PAD)
    return vec[:MAX_LEN]


def letras_pista_a_vector(letras_pista: List[str]) -> List[float]:
    vec = [0.0] * ALPHA_SIZE
    for letra in letras_pista:
        idx = CHAR_A_IDX.get(letra.lower(), None)
        if idx is not None:
            vec[idx - 1] = 1.0
    return vec


def palabra_a_one_hot(idx_palabra: int, vocab_size: int) -> np.ndarray:
    ohe = np.zeros(vocab_size, dtype=np.float32)
    ohe[idx_palabra] = 1.0
    return ohe


def generar_datos_cat1(vocabulario: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for idx, palabra in enumerate(vocabulario):
        n = len(palabra)

        # Turno 0: todo vacío
        X.append(palabra_a_vector('_' * n))
        y.append(idx)

        # Turnos 1..n: revelar letra por letra de izquierda a derecha
        for reveal_hasta in range(1, n + 1):
            patron = list('_' * n)
            for i in range(reveal_hasta):
                patron[i] = palabra[i]
            X.append(palabra_a_vector(''.join(patron)))
            y.append(idx)

        # Muestras extra: patrones con letras intermedias reveladas
        # Esto refuerza que el modelo respete posiciones fijas
        for _ in range(3):
            n_revelar = random.randint(1, n)
            posiciones = sorted(random.sample(range(n), n_revelar))
            patron = list('_' * n)
            for pos in posiciones:
                patron[pos] = palabra[pos]
            X.append(palabra_a_vector(''.join(patron)))
            y.append(idx)

    return np.array(X, dtype=np.int32), np.array(y, dtype=np.int32)


def generar_datos_cat2(vocabulario: List[str]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    XA, XB, y = [], [], []
    for idx, palabra in enumerate(vocabulario):
        n = len(palabra)
        letras_en_palabra = set(palabra)
        for reveal_hasta in range(1, n + 1):
            patron = list('_' * n)
            for i in range(reveal_hasta):
                patron[i] = palabra[i]
            num_pistas = random.randint(0, min(3, len(letras_en_palabra)))
            pistas = random.sample(list(letras_en_palabra), num_pistas)
            XA.append(palabra_a_vector(''.join(patron)))
            XB.append(letras_pista_a_vector(pistas))
            y.append(idx)
    return (np.array(XA, dtype=np.int32),
            np.array(XB, dtype=np.float32),
            np.array(y, dtype=np.int32))


def construir_modelo_cat1(vocab_words: int, embed_dim: int = 32, gru_units: int = 64):
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers

        entrada = keras.Input(shape=(MAX_LEN,), name="secuencia")
        x = layers.Embedding(VOCAB_SIZE, embed_dim, name="embedding")(entrada)
        x = layers.GRU(gru_units, name="gru")(x)
        x = layers.Dense(128, activation="relu", name="dense_oculta")(x)
        x = layers.Dropout(0.3)(x)
        salida = layers.Dense(vocab_words, activation="softmax", name="prediccion")(x)

        modelo = keras.Model(inputs=entrada, outputs=salida, name="GRU_Cat1")
        modelo.compile(
            optimizer=keras.optimizers.Adam(learning_rate=1e-3),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"]
        )
        return modelo
    except ImportError:
        return None


def construir_modelo_cat2(vocab_words: int, embed_dim: int = 32, gru_units: int = 64, dense_pistas: int = 32):
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers

        entrada_seq = keras.Input(shape=(MAX_LEN,), name="secuencia")
        x_seq = layers.Embedding(VOCAB_SIZE, embed_dim, name="embedding")(entrada_seq)
        x_seq = layers.GRU(gru_units, name="gru")(x_seq)

        entrada_pistas = keras.Input(shape=(ALPHA_SIZE,), name="pistas")
        x_pistas = layers.Dense(dense_pistas, activation="relu", name="dense_pistas")(entrada_pistas)

        fusionado = layers.Concatenate(name="fusion")([x_seq, x_pistas])
        x = layers.Dense(128, activation="relu", name="dense_fusion")(fusionado)
        x = layers.Dropout(0.3)(x)
        salida = layers.Dense(vocab_words, activation="softmax", name="prediccion")(x)

        modelo = keras.Model(
            inputs=[entrada_seq, entrada_pistas],
            outputs=salida,
            name="GRU_Cat2"
        )
        modelo.compile(
            optimizer=keras.optimizers.Adam(learning_rate=1e-3),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"]
        )
        return modelo
    except ImportError:
        return None


def entrenar(dataset_path: str, epochs_cat1: int = 40, epochs_cat2: int = 50,
             batch_size: int = 32, verbose: bool = True) -> Dict:
    try:
        import tensorflow as tf
        print(f"TensorFlow {tf.__version__} detectado.")
    except ImportError:
        print("⚠️  TensorFlow no disponible. Instala con: pip install tensorflow")
        return {}

    os.makedirs(MODELO_DIR, exist_ok=True)

    with open(dataset_path, 'r', encoding='utf-8') as f:
        ds = json.load(f)

    # Tomar corpus_gru como base
    vocabulario = []
    for cat in ds["categorias"].values():
        for p in cat["palabras"]:
            vocabulario.append(p["palabra"].lower())
    vocabulario = sorted(set(vocabulario))
    vocabulario = [p for p in vocabulario if 4 <= len(p) <= 6]

    vocab_size = len(vocabulario)

    with open(VOCAB_PATH, 'w', encoding='utf-8') as f:
        json.dump(vocabulario, f, ensure_ascii=False)
    print(f"📚 Vocabulario: {vocab_size} palabras")

    resultados = {}

    print("\n🔵 Entrenando Categoría 1 (GRU secuencial)…")
    X1, y1 = generar_datos_cat1(vocabulario)
    idx = np.random.permutation(len(X1))
    X1, y1 = X1[idx], y1[idx]

    modelo1 = construir_modelo_cat1(vocab_size)
    if modelo1:
        if verbose:
            modelo1.summary()
        hist1 = modelo1.fit(X1, y1, epochs=epochs_cat1, batch_size=batch_size,
                            validation_split=0.1, verbose=1 if verbose else 0)
        modelo1.save(MODELO_CAT1)
        resultados["cat1_acc"] = float(hist1.history["accuracy"][-1])
        print(f"✅ Cat1 guardado. Acc final: {resultados['cat1_acc']:.3f}")

    print("\n🟡 Entrenando Categoría 2 (GRU multi-input)…")
    XA2, XB2, y2 = generar_datos_cat2(vocabulario)
    idx = np.random.permutation(len(y2))
    XA2, XB2, y2 = XA2[idx], XB2[idx], y2[idx]

    modelo2 = construir_modelo_cat2(vocab_size)
    if modelo2:
        if verbose:
            modelo2.summary()
        hist2 = modelo2.fit([XA2, XB2], y2, epochs=epochs_cat2, batch_size=batch_size,
                            validation_split=0.1, verbose=1 if verbose else 0)
        modelo2.save(MODELO_CAT2)
        resultados["cat2_acc"] = float(hist2.history["accuracy"][-1])
        print(f"✅ Cat2 guardado. Acc final: {resultados['cat2_acc']:.3f}")

    print("\n🎉 Entrenamiento completo.")
    return resultados


class InferenciaGRU:
    def __init__(self, dataset_path: str):
        self.vocabulario: List[str] = []
        self.modelo_cat1 = None
        self.modelo_cat2 = None
        self.disponible = False
        self._cargar_vocabulario(dataset_path)
        self._cargar_modelos()

    def _cargar_vocabulario(self, dataset_path: str):
        # Siempre cargar desde el dataset completo, ignorar corpus_gru
        with open(dataset_path, 'r', encoding='utf-8') as f:
            ds = json.load(f)
        for cat in ds["categorias"].values():
            for p in cat["palabras"]:
                self.vocabulario.append(p["palabra"].lower())
        self.vocabulario = sorted(set(
            p for p in self.vocabulario if 4 <= len(p) <= 6
        ))
        # Si existe vocabulario.json guardado del entrenamiento, usarlo
        # solo si fue generado con el nuevo sistema (mismo tamaño o más)
        if os.path.exists(VOCAB_PATH):
            with open(VOCAB_PATH, 'r', encoding='utf-8') as f:
                guardado = json.load(f)
            if len(guardado) >= len(self.vocabulario):
                self.vocabulario = guardado

    def _cargar_modelos(self):
        try:
            import tensorflow as tf
            if os.path.exists(MODELO_CAT1):
                self.modelo_cat1 = tf.keras.models.load_model(MODELO_CAT1)
            if os.path.exists(MODELO_CAT2):
                self.modelo_cat2 = tf.keras.models.load_model(MODELO_CAT2)
            if self.modelo_cat1 or self.modelo_cat2:
                self.disponible = True
        except Exception as e:
            print(f"⚠️  Modelos GRU no cargados: {e}")

    def predecir_cat1(self, patron: str, longitud: int, top_k: int = 5) -> List[Tuple[str, float]]:
        if self.modelo_cat1 and self.disponible:
            x = np.array([palabra_a_vector(patron)], dtype=np.int32)
            probs = self.modelo_cat1.predict(x, verbose=0)[0]
            top_idx = np.argsort(probs)[::-1]  # ordenar todas, no solo top_k

            candidatos = []
            patron_lower = patron.lower()
            for i in top_idx:
                if i >= len(self.vocabulario):
                    continue
                palabra = self.vocabulario[i]
                if len(palabra) != longitud:
                    continue
                # ── FILTRO CRÍTICO: respetar letras reveladas ──
                match = True
                for pos, c in enumerate(patron_lower):
                    if c != '_' and (pos >= len(palabra) or c != palabra[pos]):
                        match = False
                        break
                if not match:
                    continue
                candidatos.append((palabra, float(probs[i])))
                if len(candidatos) >= top_k:
                    break

            if candidatos:
                return candidatos

        return self._fallback(patron, longitud, [], [])

    def predecir_cat2(self, patron: str, longitud: int, letras_pista: List[str],
                      letras_descartadas: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        if self.modelo_cat2 and self.disponible:
            x_seq = np.array([palabra_a_vector(patron)], dtype=np.int32)
            x_pist = np.array([letras_pista_a_vector(letras_pista)], dtype=np.float32)
            probs = self.modelo_cat2.predict([x_seq, x_pist], verbose=0)[0]
            top_idx = np.argsort(probs)[-top_k:][::-1]
            candidatos = [(self.vocabulario[i], float(probs[i]))
                          for i in top_idx
                          if i < len(self.vocabulario) and len(self.vocabulario[i]) == longitud]
            if candidatos:
                return candidatos
        return self._fallback(patron, longitud, letras_pista, letras_descartadas)

    def _fallback(self, patron: str, longitud: int, letras_pista: List[str],
                  letras_descartadas: List[str]) -> List[Tuple[str, float]]:
        candidatos = []
        patron_lower = patron.lower()
        letras_desc_set = set(l.lower() for l in letras_descartadas)
        letras_pista_set = set(l.lower() for l in letras_pista)

        for palabra in self.vocabulario:
            if len(palabra) != longitud:
                continue
            match = True
            for i, c in enumerate(patron_lower):
                if i >= len(palabra):
                    match = False
                    break
                if c != '_' and c != palabra[i]:
                    match = False
                    break
            if not match:
                continue
            if any(l in palabra for l in letras_desc_set):
                continue
            if not all(l in palabra for l in letras_pista_set):
                continue
            candidatos.append((palabra, 1.0))

        if not candidatos:
            candidatos = [(p, 0.5) for p in self.vocabulario if len(p) == longitud]

        random.shuffle(candidatos)
        return candidatos[:5] if candidatos else [("-----"[:longitud], 0.0)]


if __name__ == "__main__":
    import sys
    dataset = os.path.join(os.path.dirname(__file__), "..", "dataset", "palabras_es.json")
    if not os.path.exists(dataset):
        print("❌ Dataset no encontrado.")
        sys.exit(1)
    entrenar(dataset, epochs_cat1=30, epochs_cat2=40, verbose=True)
