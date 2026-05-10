# GRUdle-Deep-Learning-Game
GRUdle es un juego donde compites contra una IA (red neuronal GRU) para adivinar una palabra oculta letra por letra. El humano conoce la categoría; la IA usa Deep Learning. Ofrece dos modos: uno de predicción secuencial básica y otro avanzado (multi-input) donde la IA memoriza letras acertadas de intentos previos para afinar su predicción.

# ⚔ Duelo de Palabras
### Humano vs. Inteligencia Artificial — Adivina la Palabra

---

## 🎮 Descripción

**Duelo de Palabras** es un juego competitivo donde un jugador humano se enfrenta a una red neuronal GRU en tiempo real. Ambos deben adivinar una palabra secreta que se revela letra por letra, turno a turno.

### Mecánicas principales
- **6 turnos máximos** por partida
- **30 segundos** por turno (sincronizados)
- **Letras verdes**: reveladas automáticamente al inicio de cada turno
- **Letras grises**: existen en la palabra (posición incorrecta o correcta)
- **Letras oscuras**: no pertenecen a la palabra
- **Ahorcado**: penalización visual por error

### Asimetría estratégica
| | Humano | IA |
|---|---|---|
| Ve la categoría | ✅ Sí | ❌ No |
| Usa patrones lingüísticos | Limitado | ✅ Completo |
| Aprende de pistas grises | ✅ | ✅ (Cat2) |

---

## 📁 Estructura del Proyecto

```
duelo_palabras/
├── main.py                  # Punto de entrada
├── entrenar.py              # Script de entrenamiento GRU
├── requirements.txt         # Dependencias Python
│
├── dataset/
│   └── palabras_es.json     # Dataset completo (~480 palabras, 6 categorías)
│
├── model/
│   ├── gru.py               # Arquitectura y entrenamiento GRU
│   └── pesos/               # Modelos entrenados (.keras)
│       ├── gru_cat1.keras
│       ├── gru_cat2.keras
│       └── vocabulario.json
│
├── juego/
│   ├── logica.py            # Motor del juego (estado, evaluación)
│   └── agente_ia.py         # Agente IA con threading
│
└── gui/
    └── main_gui.py          # Interfaz gráfica tkinter
```

---

## 🚀 Instalación y Uso

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
# Para GPU (opcional):
pip install tensorflow[and-cuda]
```

### 2. Entrenar los modelos GRU (opcional)
```bash
# Entrenamiento básico
python entrenar.py

# Con más épocas para mejor rendimiento
python entrenar.py --epochs-cat1 80 --epochs-cat2 100

# En Google Colab con GPU
python entrenar.py --colab --epochs-cat1 60 --epochs-cat2 80
```

> **Sin entrenamiento**: el juego funciona con un motor heurístico de búsqueda en vocabulario. Con los modelos GRU entrenados, la IA mejora significativamente.

### 3. Lanzar el juego
```bash
python main.py
```

---

## 🧠 Arquitectura de la IA

### Categoría 1 — GRU Secuencial
```
Entrada: [7, 0, 0, 0, 0]  → "G____"
    ↓
Embedding (32 dims)
    ↓
GRU (64 unidades)
    ↓
Dense (128) + Dropout(0.3)
    ↓
Softmax → Predicción de palabra
```

### Categoría 2 — Multi-Input GRU
```
Rama A: Secuencia  →  Embedding → GRU(64)  ──┐
                                               Concatenate → Dense(128) → Softmax
Rama B: Pistas     →  Dense(32)            ──┘
```

### Feedback de colores
- 🟢 **Verde**: Letra revelada por el juego (posición correcta, forzada)
- 🔵 **Gris**: Letra existe en la palabra (posición desconocida)
- ⬛ **Oscuro**: Letra no está en la palabra

---

## 📊 Dataset

El archivo `dataset/palabras_es.json` contiene:

| Categoría | Palabras |
|-----------|----------|
| 🦁 Animales | 80 palabras |
| 🔧 Objetos | 80 palabras |
| 👩‍⚕️ Profesiones | 80 palabras |
| 🌿 Naturaleza | 80 palabras |
| 🍕 Comida | 80 palabras |
| 🏙️ Lugares | 80 palabras |

Cada palabra incluye: `longitud`, `frecuencia` (0-100), y categoría.

El campo `corpus_gru` contiene el vocabulario de entrenamiento para la red neuronal.

---

## 🎯 Modos de Dificultad

| Modo | IA recibe | Ventaja humano |
|------|-----------|----------------|
| 🔵 Básico (Cat1) | Solo letras reveladas | Categoría |
| 🟡 Avanzado (Cat2) | Letras reveladas + pistas grises | Solo categoría |

---

## 🛠 Google Colab

Para entrenar con GPU gratuita en Google Colab:

```python
# En una celda de Colab:
!git clone <tu-repo> duelo
%cd duelo
!pip install tensorflow numpy

!python entrenar.py --colab --epochs-cat1 80 --epochs-cat2 100

# Descargar los pesos
from google.colab import files
import zipfile

with zipfile.ZipFile('pesos.zip', 'w') as z:
    import glob
    for f in glob.glob('model/pesos/*'):
        z.write(f)

files.download('pesos.zip')
```

Luego extrae `pesos.zip` en la carpeta `model/pesos/` de tu instalación local.

---

## ⚙️ Requisitos

- **Python** 3.9+
- **tkinter** (incluido en Python estándar)
- **tensorflow** 2.12+ (solo para entrenar/usar GRU)
- **numpy** 1.23+

### Linux (si falta tkinter):
```bash
sudo apt-get install python3-tk
```

---

## 📝 Licencia

Proyecto educativo de demostración de redes neuronales GRU aplicadas a juegos de palabras.

