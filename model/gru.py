"""
Modelos de IA para Duelo de Palabras — dos entrenamientos completamente separados.

══════════════════════════════════════════════════════════════════════
NIVEL 1 — GRU Secuencial Puro
══════════════════════════════════════════════════════════════════════
Arquitectura: Embedding → GRU → Dense → Softmax
Datos de entrenamiento: SOLO la secuencia de letras reveladas de
  izquierda a derecha. El patrón del turno 0 es todo ceros (____),
  turno 1 es la primera letra revelada (G____), etc.
NO se incluyen patrones con posiciones aleatorias ni pistas grises.
La IA de nivel 1 NO recibe retroalimentación de colores; solo ve
el prefijo que el juego le da cada turno.

══════════════════════════════════════════════════════════════════════
NIVEL 2 — MLP Multi-Input con Feedback Completo
══════════════════════════════════════════════════════════════════════
Arquitectura: [vector_posiciones_verdes + vector_letras_grises +
               vector_letras_azules + vector_letras_descartadas]
              → Dense(256) → Dense(128) → Softmax
Datos de entrenamiento: simulación de N partidas Wordle completas.
  Cada ejemplo es el estado acumulado después de k intentos:
    · Qué letras están confirmadas en qué posición (verdes)
    · Qué letras existen pero posición incorrecta (grises)
    · Qué letras existen y son dobles (azules)
    · Qué letras están descartadas (oscuras)
La IA de nivel 2 usa esta información para filtrar y puntuar palabras.
"""

import os
import json
import random
import numpy as np
from collections import Counter
from typing import List, Tuple, Dict, Optional

# ── Constantes ────────────────────────────────────────────────────────────────
PAD      = 0
LETRAS   = "abcdefghijklmnopqrstuvwxyzáéíóúüñ"
# Usamos solo ASCII básico + ñ para tokenización simple
LETRAS_B = "abcdefghijklmnopqrstuvwxyzñ"
CHAR_A_IDX = {c: i + 1 for i, c in enumerate(LETRAS_B)}
IDX_A_CHAR = {v: k for k, v in CHAR_A_IDX.items()}
VOCAB_SIZE = 28   # 26 letras + ñ + PAD
ALPHA_SIZE = 26
MAX_LEN    = 10   # longitud máxima soportada

MODELO_DIR  = os.path.join(os.path.dirname(__file__), "pesos")
MODELO_N1   = os.path.join(MODELO_DIR, "gru_nivel1.keras")
MODELO_N2   = os.path.join(MODELO_DIR, "mlp_nivel2.keras")
VOCAB_N1    = os.path.join(MODELO_DIR, "vocab_nivel1.json")
VOCAB_N2    = os.path.join(MODELO_DIR, "vocab_nivel2.json")


# ── Helpers de tokenización ───────────────────────────────────────────────────

def _norm(letra: str) -> str:
    """Normaliza letra: quita tildes, pasa a minúscula. Conserva la ñ."""
    return (letra.lower()
            .replace('á','a').replace('é','e').replace('í','i')
            .replace('ó','o').replace('ú','u').replace('ü','u'))


def patron_a_vector_n1(patron: str, max_len: int = MAX_LEN) -> List[int]:
    """Para nivel 1: convierte el prefijo revelado en vector de ints."""
    vec = []
    for c in patron.lower():
        if c in ('_', ' '):
            vec.append(PAD)
        else:
            vec.append(CHAR_A_IDX.get(_norm(c), PAD))
    while len(vec) < max_len:
        vec.append(PAD)
    return vec[:max_len]


def estado_n2_a_vector(verdes: Dict[int, str], grises: List[str],
                        azules: List[str], descartadas: List[str],
                        longitud: int) -> np.ndarray:
    """
    Para nivel 2: codifica el estado completo de pistas como un vector denso.

    Estructura del vector (todo concatenado):
      · longitud * ALPHA_SIZE  → one-hot por posición de letras verdes confirmadas
      · ALPHA_SIZE             → letras grises (existen, pos incorrecta)
      · ALPHA_SIZE             → letras azules (existen, son dobles)
      · ALPHA_SIZE             → letras descartadas
      · MAX_LEN bits           → one-hot de longitud
    """
    dim_pos   = longitud * ALPHA_SIZE
    dim_total = dim_pos + 3 * ALPHA_SIZE + MAX_LEN

    v = np.zeros(dim_total, dtype=np.float32)

    # Verdes: one-hot por posición
    for pos, letra in verdes.items():
        idx = CHAR_A_IDX.get(_norm(letra), None)
        if idx and pos < longitud:
            v[pos * ALPHA_SIZE + (idx - 1)] = 1.0

    # Grises
    offset = dim_pos
    for letra in grises:
        idx = CHAR_A_IDX.get(_norm(letra), None)
        if idx:
            v[offset + idx - 1] = 1.0

    # Azules
    offset += ALPHA_SIZE
    for letra in azules:
        idx = CHAR_A_IDX.get(_norm(letra), None)
        if idx:
            v[offset + idx - 1] = 1.0

    # Descartadas
    offset += ALPHA_SIZE
    for letra in descartadas:
        idx = CHAR_A_IDX.get(_norm(letra), None)
        if idx:
            v[offset + idx - 1] = 1.0

    # Longitud (one-hot)
    offset += ALPHA_SIZE
    if 0 <= longitud - 1 < MAX_LEN:
        v[offset + longitud - 1] = 1.0

    return v


def _dim_n2(longitud: int) -> int:
    return longitud * ALPHA_SIZE + 3 * ALPHA_SIZE + MAX_LEN


# ── Evaluación local para generar datos de entrenamiento de nivel 2 ───────────
def _evaluar_wordle(intento: str, secreta: str) -> List[str]:
    """Devuelve lista de colores: 'verde', 'gris', 'azul', 'oscuro'."""
    n = len(secreta)
    colores = ['oscuro'] * n
    freq    = Counter(secreta)

    # Pasada 1: verdes exactos
    for i, c in enumerate(intento):
        if i < n and c == secreta[i]:
            colores[i] = 'verde'
            freq[c] -= 1

    # Pasada 2: grises / azules
    for i, c in enumerate(intento):
        if colores[i] == 'verde':
            continue
        if c in secreta and freq.get(c, 0) > 0:
            # ¿Aparece más de una vez en la secreta?
            if Counter(secreta)[c] > 1:
                colores[i] = 'azul'
            else:
                colores[i] = 'gris'
            freq[c] -= 1

    return colores


# ══════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

def generar_datos_nivel1(vocabulario: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Nivel 1 — GRU secuencial puro.
    Solo genera patrones de revelación ESTRICTA de izquierda a derecha.
    NO se incluyen posiciones aleatorias ni pistas de colores.

    Por cada palabra genera:
      turno 0: ____ (todo vacío)
      turno 1: G___ (primera letra)
      turno 2: GA__ (dos primeras)
      ... etc.
    """
    X, y = [], []
    for idx, palabra in enumerate(vocabulario):
        n = len(palabra)
        # Turno 0: todo vacío
        X.append(patron_a_vector_n1('_' * n))
        y.append(idx)
        # Turnos 1..n: revelar de izquierda a derecha
        for k in range(1, n + 1):
            patron = palabra[:k] + '_' * (n - k)
            X.append(patron_a_vector_n1(patron))
            y.append(idx)
    return np.array(X, dtype=np.int32), np.array(y, dtype=np.int32)


def generar_datos_nivel2(vocabulario: List[str],
                          muestras_por_palabra: int = 12) -> Tuple[np.ndarray, np.ndarray]:
    """
    Nivel 2 — MLP con feedback completo.
    Simula partidas Wordle reales y acumula el estado de pistas.

    Por cada palabra genera muestras_por_palabra escenarios:
      - Se eligen k intentos previos aleatorios del vocabulario
      - Se evalúan contra la palabra secreta
      - Se acumula el estado (verdes, grises, azules, descartadas)
      - Esa es la entrada; la salida es el índice de la palabra secreta
    """
    # Agrupar por longitud para búsquedas rápidas
    por_longitud: Dict[int, List[str]] = {}
    for p in vocabulario:
        por_longitud.setdefault(len(p), []).append(p)

    X_list, y_list = [], []
    max_dim = max(_dim_n2(l) for l in por_longitud) if por_longitud else _dim_n2(6)

    for idx, secreta in enumerate(vocabulario):
        n       = len(secreta)
        cands   = por_longitud.get(n, [secreta])
        longitud = n

        for _ in range(muestras_por_palabra):
            # Simular entre 0 y MAX_TURNOS-1 intentos previos
            n_prev = random.randint(0, 5)
            intentos_prev = random.choices(cands, k=n_prev) if n_prev > 0 else []

            verdes:      Dict[int, str] = {}
            grises:      set = set()
            azules:      set = set()
            descartadas: set = set()

            for intento in intentos_prev:
                if len(intento) != n:
                    continue
                colores = _evaluar_wordle(intento, secreta)
                for i, (c, col) in enumerate(zip(intento, colores)):
                    if col == 'verde':
                        verdes[i] = c
                    elif col == 'gris':
                        grises.add(c)
                    elif col == 'azul':
                        azules.add(c)
                    elif col == 'oscuro':
                        descartadas.add(c)

            vec = estado_n2_a_vector(verdes, list(grises), list(azules),
                                      list(descartadas), longitud)

            # Pad o truncar al max_dim uniforme
            if len(vec) < max_dim:
                vec = np.pad(vec, (0, max_dim - len(vec)))
            X_list.append(vec[:max_dim])
            y_list.append(idx)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE MODELOS
# ══════════════════════════════════════════════════════════════════════════════

def construir_modelo_nivel1(vocab_size: int, embed_dim: int = 32,
                             gru_units: int = 128):
    """
    GRU secuencial para nivel 1.
    Embedding → GRU → Dense → Softmax
    """
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers

        entrada = keras.Input(shape=(MAX_LEN,), name="secuencia")
        x = layers.Embedding(VOCAB_SIZE, embed_dim,
                              mask_zero=True, name="embedding")(entrada)
        x = layers.GRU(gru_units, name="gru")(x)
        x = layers.Dense(256, activation="relu")(x)
        x = layers.Dropout(0.3)(x)
        x = layers.Dense(128, activation="relu")(x)
        x = layers.Dropout(0.2)(x)
        salida = layers.Dense(vocab_size, activation="softmax",
                               name="prediccion")(x)

        modelo = keras.Model(inputs=entrada, outputs=salida,
                              name="GRU_Nivel1")
        modelo.compile(
            optimizer=keras.optimizers.Adam(learning_rate=5e-4),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"]
        )
        return modelo
    except ImportError:
        return None


def construir_modelo_nivel2(input_dim: int, vocab_size: int):
    """
    MLP multi-input para nivel 2.
    Toma el vector de estado completo (verdes + grises + azules + descartadas)
    y predice la palabra más probable del vocabulario.
    """
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers

        entrada = keras.Input(shape=(input_dim,), name="estado_pistas")
        x = layers.Dense(512, activation="relu")(entrada)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.3)(x)
        x = layers.Dense(256, activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(128, activation="relu")(x)
        x = layers.Dropout(0.1)(x)
        salida = layers.Dense(vocab_size, activation="softmax",
                               name="prediccion")(x)

        modelo = keras.Model(inputs=entrada, outputs=salida,
                              name="MLP_Nivel2")
        modelo.compile(
            optimizer=keras.optimizers.Adam(learning_rate=5e-4),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"]
        )
        return modelo
    except ImportError:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL DE ENTRENAMIENTO
# ══════════════════════════════════════════════════════════════════════════════

def entrenar(dataset_path: str,
             epochs_n1: int = 50,
             epochs_n2: int = 60,
             batch_size: int = 32,
             verbose: bool = True) -> Dict:
    try:
        import tensorflow as tf
        print(f"TensorFlow {tf.__version__} detectado.")
        try:
            from tensorflow.keras import mixed_precision
            mixed_precision.set_global_policy('mixed_float16')
            print("  → Precisión mixta habilitada")
        except Exception:
            pass
    except ImportError:
        print("⚠️  TensorFlow no disponible. Instala con: pip install tensorflow")
        return {}

    os.makedirs(MODELO_DIR, exist_ok=True)

    with open(dataset_path, 'r', encoding='utf-8') as f:
        ds = json.load(f)

    # Vocabulario compartido (todas las palabras del dataset)
    vocab_bruto = []
    for cat in ds["categorias"].values():
        for p in cat["palabras"]:
            vocab_bruto.append(_norm(p["palabra"]))
    vocab_bruto = sorted(set(vocab_bruto))
    vocab_bruto = [p for p in vocab_bruto if 4 <= len(p) <= MAX_LEN and p.isalpha()]

    resultados = {}

    # ═══════════════════════════════════════════════════════
    # ENTRENAMIENTO NIVEL 1 — GRU Secuencial Puro
    # ═══════════════════════════════════════════════════════
    print("\n" + "═"*56)
    print("  NIVEL 1 — GRU Secuencial Puro")
    print("  Entrada: solo prefijo revelado de izquierda a derecha")
    print("  Sin pistas de colores")
    print("═"*56)

    vocab_n1 = vocab_bruto  # todas las palabras del dataset
    print(f"  Vocabulario N1: {len(vocab_n1)} palabras")

    with open(VOCAB_N1, 'w', encoding='utf-8') as f:
        json.dump(vocab_n1, f, ensure_ascii=False)

    X1, y1 = generar_datos_nivel1(vocab_n1)
    print(f"  Muestras generadas: {len(X1)}")
    idx = np.random.permutation(len(X1))
    X1, y1 = X1[idx], y1[idx]

    modelo_n1 = construir_modelo_nivel1(len(vocab_n1))
    if modelo_n1:
        if verbose:
            modelo_n1.summary()
        cb = [tf.keras.callbacks.EarlyStopping(
                  monitor='val_accuracy', patience=8,
                  restore_best_weights=True, verbose=1),
              tf.keras.callbacks.ReduceLROnPlateau(
                  monitor='val_loss', factor=0.5, patience=4, verbose=1)]
        hist1 = modelo_n1.fit(
            X1, y1,
            epochs=epochs_n1,
            batch_size=batch_size,
            validation_split=0.1,
            callbacks=cb,
            verbose=1 if verbose else 0
        )
        modelo_n1.save(MODELO_N1)
        resultados["n1_acc"] = float(hist1.history["accuracy"][-1])
        print(f"\n  ✅ Nivel 1 guardado → {MODELO_N1}")
        print(f"  Accuracy final: {resultados['n1_acc']:.3f}")

    # ═══════════════════════════════════════════════════════
    # ENTRENAMIENTO NIVEL 2 — MLP con Feedback Completo
    # ═══════════════════════════════════════════════════════
    print("\n" + "═"*56)
    print("  NIVEL 2 — MLP con Feedback Completo (Wordle)")
    print("  Entrada: verdes + grises + azules + descartadas")
    print("  Sin letras reveladas automáticas")
    print("═"*56)

    vocab_n2 = vocab_bruto
    print(f"  Vocabulario N2: {len(vocab_n2)} palabras")

    with open(VOCAB_N2, 'w', encoding='utf-8') as f:
        json.dump(vocab_n2, f, ensure_ascii=False)

    X2, y2 = generar_datos_nivel2(vocab_n2, muestras_por_palabra=15)
    print(f"  Muestras generadas: {len(X2)}")
    idx = np.random.permutation(len(y2))
    X2, y2 = X2[idx], y2[idx]

    input_dim_n2 = X2.shape[1]
    # Guardar dimensión para inferencia
    meta = {"input_dim": input_dim_n2, "max_longitud": MAX_LEN}
    with open(os.path.join(MODELO_DIR, "meta_nivel2.json"), 'w') as f:
        json.dump(meta, f)

    modelo_n2 = construir_modelo_nivel2(input_dim_n2, len(vocab_n2))
    if modelo_n2:
        if verbose:
            modelo_n2.summary()
        cb2 = [tf.keras.callbacks.EarlyStopping(
                   monitor='val_accuracy', patience=10,
                   restore_best_weights=True, verbose=1),
               tf.keras.callbacks.ReduceLROnPlateau(
                   monitor='val_loss', factor=0.5, patience=5, verbose=1)]
        hist2 = modelo_n2.fit(
            X2, y2,
            epochs=epochs_n2,
            batch_size=batch_size,
            validation_split=0.1,
            callbacks=cb2,
            verbose=1 if verbose else 0
        )
        modelo_n2.save(MODELO_N2)
        resultados["n2_acc"] = float(hist2.history["accuracy"][-1])
        print(f"\n  ✅ Nivel 2 guardado → {MODELO_N2}")
        print(f"  Accuracy final: {resultados['n2_acc']:.3f}")

    print("\n🎉 Entrenamiento completo. Ambos modelos guardados en model/pesos/")
    return resultados


# ══════════════════════════════════════════════════════════════════════════════
# INFERENCIA EN TIEMPO REAL
# ══════════════════════════════════════════════════════════════════════════════

class InferenciaGRU:
    """
    Gestiona la inferencia para ambos niveles.
    · Nivel 1: usa el modelo GRU con el prefijo revelado.
    · Nivel 2: usa el modelo MLP con el estado completo de pistas.
    Si los modelos no están entrenados, cae a heurística de vocabulario.
    """

    def __init__(self, dataset_path: str):
        self.vocab_n1:     List[str] = []
        self.vocab_n2:     List[str] = []
        self.modelo_n1               = None
        self.modelo_n2               = None
        self.input_dim_n2: int       = 0
        self.disponible_n1: bool     = False
        self.disponible_n2: bool     = False
        self._cargar_vocabs(dataset_path)
        self._cargar_modelos()

    @property
    def disponible(self) -> bool:
        return self.disponible_n1 or self.disponible_n2

    def _cargar_vocabs(self, dataset_path: str):
        # Vocabulario base desde el dataset
        with open(dataset_path, 'r', encoding='utf-8') as f:
            ds = json.load(f)
        base = []
        for cat in ds["categorias"].values():
            for p in cat["palabras"]:
                base.append(_norm(p["palabra"]))
        base = sorted(set(p for p in base if 4 <= len(p) <= MAX_LEN and p.isalpha()))

        # Cargar vocab entrenado si existe (puede ser más grande)
        if os.path.exists(VOCAB_N1):
            with open(VOCAB_N1, 'r', encoding='utf-8') as f:
                self.vocab_n1 = json.load(f)
        else:
            self.vocab_n1 = base

        if os.path.exists(VOCAB_N2):
            with open(VOCAB_N2, 'r', encoding='utf-8') as f:
                self.vocab_n2 = json.load(f)
        else:
            self.vocab_n2 = base

    def _cargar_modelos(self):
        try:
            import tensorflow as tf

            if os.path.exists(MODELO_N1):
                self.modelo_n1   = tf.keras.models.load_model(MODELO_N1)
                self.disponible_n1 = True
                print("✅ Modelo Nivel 1 (GRU) cargado.")

            if os.path.exists(MODELO_N2):
                self.modelo_n2   = tf.keras.models.load_model(MODELO_N2)
                meta_path = os.path.join(MODELO_DIR, "meta_nivel2.json")
                if os.path.exists(meta_path):
                    with open(meta_path) as f:
                        meta = json.load(f)
                    self.input_dim_n2 = meta["input_dim"]
                self.disponible_n2 = True
                print("✅ Modelo Nivel 2 (MLP) cargado.")

        except Exception as e:
            print(f"⚠️  Modelos no cargados: {e}")

    # ── Predicción Nivel 1 ────────────────────────────────────────────────────
    def predecir_nivel1(self, patron: str, longitud: int,
                         top_k: int = 8) -> List[Tuple[str, float]]:
        """
        Solo usa el prefijo revelado (izquierda a derecha).
        NO recibe ninguna pista de colores.
        """
        vocab = self.vocab_n1

        if self.disponible_n1 and self.modelo_n1:
            try:
                x = np.array([patron_a_vector_n1(patron)], dtype=np.int32)
                probs = self.modelo_n1.predict(x, verbose=0)[0]
                orden = np.argsort(probs)[::-1]

                candidatos = []
                patron_l   = patron.lower()
                for i in orden:
                    if i >= len(vocab): continue
                    palabra = vocab[i]
                    if len(palabra) != longitud: continue
                    # Respetar el prefijo revelado estrictamente
                    if not _match_patron(palabra, patron_l): continue
                    candidatos.append((palabra, float(probs[i])))
                    if len(candidatos) >= top_k: break

                if candidatos:
                    return candidatos
            except Exception as e:
                print(f"⚠️  Error inferencia N1: {e}")

        return self._fallback_n1(patron, longitud, vocab)

    # ── Predicción Nivel 2 ────────────────────────────────────────────────────
    def predecir_nivel2(self, longitud: int,
                         verdes: Dict[int, str],
                         grises: List[str],
                         azules: List[str],
                         descartadas: List[str],
                         top_k: int = 8) -> List[Tuple[str, float]]:
        """
        Usa el estado completo de pistas de colores.
        NO usa el prefijo revelado (nivel 2 no revela letras automáticamente).
        """
        vocab = self.vocab_n2

        if self.disponible_n2 and self.modelo_n2 and self.input_dim_n2 > 0:
            try:
                vec = estado_n2_a_vector(verdes, grises, azules,
                                          descartadas, longitud)
                if len(vec) < self.input_dim_n2:
                    vec = np.pad(vec, (0, self.input_dim_n2 - len(vec)))
                vec = vec[:self.input_dim_n2]

                x     = vec.reshape(1, -1)
                probs = self.modelo_n2.predict(x, verbose=0)[0]
                orden = np.argsort(probs)[::-1]

                candidatos = []
                for i in orden:
                    if i >= len(vocab): continue
                    palabra = vocab[i]
                    if len(palabra) != longitud: continue
                    # Filtrar por restricciones duras
                    if not _cumple_restricciones(palabra, verdes, grises,
                                                  azules, descartadas):
                        continue
                    candidatos.append((palabra, float(probs[i])))
                    if len(candidatos) >= top_k: break

                if candidatos:
                    return candidatos
            except Exception as e:
                print(f"⚠️  Error inferencia N2: {e}")

        return self._fallback_n2(longitud, verdes, grises, azules,
                                  descartadas, vocab)

    # ── Fallbacks heurísticos ────────────────────────────────────────────────
    def _fallback_n1(self, patron: str, longitud: int,
                      vocab: List[str]) -> List[Tuple[str, float]]:
        """Nivel 1: filtra por longitud y patrón, sin pistas."""
        patron_l   = patron.lower()
        candidatos = [(p, 1.0) for p in vocab
                      if len(p) == longitud and _match_patron(p, patron_l)]
        if not candidatos:
            candidatos = [(p, 0.5) for p in vocab if len(p) == longitud]
        random.shuffle(candidatos)
        return candidatos[:8]

    def _fallback_n2(self, longitud: int, verdes: Dict[int, str],
                      grises: List[str], azules: List[str],
                      descartadas: List[str],
                      vocab: List[str]) -> List[Tuple[str, float]]:
        """Nivel 2: filtra por todas las restricciones de color."""
        candidatos = [
            (p, 1.0) for p in vocab
            if len(p) == longitud and
               _cumple_restricciones(p, verdes, grises, azules, descartadas)
        ]
        if not candidatos:
            candidatos = [(p, 0.5) for p in vocab if len(p) == longitud]
        random.shuffle(candidatos)
        return candidatos[:8]


# ── Funciones de filtrado ──────────────────────────────────────────────────────

def _norm(letra: str) -> str:
    return (letra.lower()
            .replace('á','a').replace('é','e').replace('í','i')
            .replace('ó','o').replace('ú','u').replace('ü','u')
            .replace('ñ','n'))


def _match_patron(palabra: str, patron: str) -> bool:
    """¿La palabra respeta el prefijo revelado?"""
    for i, c in enumerate(patron):
        if c != '_' and (i >= len(palabra) or c != palabra[i]):
            return False
    return True


def _cumple_restricciones(palabra: str,
                            verdes:      Dict[int, str],
                            grises:      List[str],
                            azules:      List[str],
                            descartadas: List[str]) -> bool:
    """
    Filtra candidatos para nivel 2:
      · Las posiciones verdes deben coincidir exactamente.
      · Las letras grises y azules deben estar en la palabra.
      · Las letras descartadas NO deben estar (salvo que sean también grises/azules).
    """
    # Verdes: posición exacta
    for pos, letra in verdes.items():
        if pos >= len(palabra) or palabra[pos] != letra:
            return False

    # Grises y azules: deben estar en la palabra
    pista_set = set(list(grises) + list(azules))
    for letra in pista_set:
        if letra not in palabra:
            return False

    # Descartadas: no deben estar (excepto si también son pista)
    for letra in descartadas:
        if letra not in pista_set and letra in palabra:
            return False

    return True


if __name__ == "__main__":
    import sys
    dataset = os.path.join(os.path.dirname(__file__), "..", "dataset", "palabras_es.json")
    if not os.path.exists(dataset):
        print("❌ Dataset no encontrado.")
        sys.exit(1)
    entrenar(dataset, epochs_n1=50, epochs_n2=60, verbose=True)