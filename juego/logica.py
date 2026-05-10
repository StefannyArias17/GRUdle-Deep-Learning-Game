"""
Lógica central del juego Duelo de Palabras.

NIVEL 1 — GRU Secuencial
  · Al inicio del turno 1 se revela la primera letra (izquierda).
  · Cada turno revela una letra más, siempre de izquierda a derecha.
  · Feedback: VERDE = posición revelada, GRIS = letra existe, OSCURO = no existe.

NIVEL 2 — Feedback completo (sin letras reveladas)
  · Las casillas empiezan completamente vacías.
  · El jugador y la IA eligen cualquier palabra del vocabulario.
  · Feedback: VERDE = letra en posición exacta, GRIS = letra existe en otra
    posición, AZUL = letra existe y aparece más de una vez en la palabra secreta,
    OSCURO = no existe.
  · Nunca se revelan letras automáticamente.
"""

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple


class EstadoCasilla(Enum):
    VACIO  = "vacio"
    VERDE  = "verde"   # Letra en posición exacta
    GRIS   = "gris"    # Letra existe pero posición incorrecta / revelada
    AZUL   = "azul"    # Letra existe y aparece más de una vez (solo nivel 2)
    OSCURO = "oscuro"  # Letra no está en la palabra
    ACTIVO = "activo"  # Casilla de escritura activa


@dataclass
class ResultadoTurno:
    palabra: str
    colores: List[EstadoCasilla]
    acerto: bool
    tiempo_respuesta: float = 0.0


@dataclass
class EstadoJugador:
    intentos:  List[str]                  = field(default_factory=list)
    feedbacks: List[List[EstadoCasilla]]  = field(default_factory=list)
    errores:   int   = 0
    gano:      bool  = False
    perdio:    bool  = False


@dataclass
class HistorialIA:
    turno:        int
    patron:       str
    letras_pista: List[str]
    candidatos:   List[Tuple[str, float]]
    seleccionada: str
    tiempo_ms:    float


class GestorJuego:
    MAX_TURNOS   = 6
    TIEMPO_TURNO = 30

    def __init__(self, dataset_path: str):
        self.dataset = self._cargar_dataset(dataset_path)
        self.nivel   = "nivel1"   # "nivel1" | "nivel2"
        self.estado  = "espera"
        self.reset()

    def _cargar_dataset(self, path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reset(self):
        self.turno_actual       = 0
        self.palabra_secreta    = ""
        self.categoria         = ""
        self.longitud_palabra  = 5
        # Solo nivel 1 usa letras_reveladas
        self.letras_reveladas:  List[Optional[str]] = []
        self.humano             = EstadoJugador()
        self.ia                 = EstadoJugador()
        self.historial_ia:      List[HistorialIA] = []
        self.estado             = "espera"
        self.humano_envio       = False
        self.ia_envio           = False
        self.intento_humano_pendiente = ""
        self.intento_ia_pendiente     = ""

    # ─── Inicio de partida ───────────────────────────────────────────────────
    def iniciar_partida(self, categoria: str, longitud: int,
                        nivel: str = "nivel1") -> str:
        self.reset()
        self.nivel            = nivel
        self.categoria        = categoria
        self.longitud_palabra = longitud
        self.palabra_secreta  = self._seleccionar_palabra(categoria, longitud)
        self.estado           = "jugando"

        if self.nivel == "nivel1":
            # Nivel 1: comienza con la primera letra ya revelada
            self.letras_reveladas = [None] * len(self.palabra_secreta)
            self._revelar_siguiente_letra()
        else:
            # Nivel 2: tablero completamente vacío
            self.letras_reveladas = [None] * len(self.palabra_secreta)

        return self.palabra_secreta

    def _seleccionar_palabra(self, categoria: str, longitud: int) -> str:
        cat_data  = self.dataset["categorias"].get(categoria, {})
        palabras  = cat_data.get("palabras", [])
        alta      = [p["palabra"].upper() for p in palabras
                     if p["longitud"] == longitud and p.get("frecuencia", 0) >= 70]
        todas     = [p["palabra"].upper() for p in palabras if p["longitud"] == longitud]
        pool      = alta if alta else todas
        if not pool:
            pool = []
            for cat in self.dataset["categorias"].values():
                pool.extend(p["palabra"].upper() for p in cat["palabras"]
                            if p["longitud"] == longitud)
        if not pool:
            pool = ["GATO"] if longitud == 4 else ["PERRO"] if longitud == 5 else ["NUTRIA"]
        return random.choice(pool)

    # ─── Letras reveladas (solo nivel 1) ────────────────────────────────────
    def _revelar_siguiente_letra(self) -> int:
        for i, letra in enumerate(self.letras_reveladas):
            if letra is None:
                self.letras_reveladas[i] = self.palabra_secreta[i]
                return i
        return -1

    def get_patron_actual(self) -> str:
        """Patrón de letras reveladas para la IA de nivel 1 ('G____')."""
        return "".join(l if l else "_" for l in self.letras_reveladas)

    # ─── Evaluación de intentos ──────────────────────────────────────────────
    def evaluar_intento(self, intento: str,
                        es_ia: bool) -> Optional[ResultadoTurno]:
        if self.estado != "jugando":
            return None
        intento = intento.upper().strip()
        if len(intento) != len(self.palabra_secreta):
            return None

        jugador = self.ia if es_ia else self.humano
        acerto  = (intento == self.palabra_secreta)

        if self.nivel == "nivel1":
            colores = self._evaluar_nivel1(intento)
        else:
            colores = self._evaluar_nivel2(intento)

        jugador.intentos.append(intento)
        jugador.feedbacks.append(colores)
        if acerto:
            jugador.gano = True

        return ResultadoTurno(intento, colores, acerto)

    def _evaluar_nivel1(self, intento: str) -> List[EstadoCasilla]:
        """
        Nivel 1:
          - Posición revelada (verde forzada) → VERDE
          - Letra existe en la palabra → GRIS  (no se distingue posición exacta)
          - Letra no existe → OSCURO
        """
        colores = []
        for i, letra in enumerate(intento):
            if self.letras_reveladas[i] is not None:
                colores.append(EstadoCasilla.VERDE)
            elif letra in self.palabra_secreta:
                colores.append(EstadoCasilla.GRIS)
            else:
                colores.append(EstadoCasilla.OSCURO)
        return colores

    def _evaluar_nivel2(self, intento: str) -> List[EstadoCasilla]:
        """
        Nivel 2 — Wordle completo:
          - Letra en posición exacta → VERDE
          - Letra existe y aparece más de una vez en la secreta → AZUL
          - Letra existe una sola vez (posición incorrecta) → GRIS
          - Letra no existe → OSCURO

        Algoritmo en dos pasadas para manejar letras repetidas correctamente.
        """
        secreta  = self.palabra_secreta
        n        = len(secreta)
        colores  = [EstadoCasilla.OSCURO] * n
        usadas   = [False] * n          # posiciones de la secreta ya asignadas

        # Pasada 1: verdes exactos
        for i, letra in enumerate(intento):
            if i < n and letra == secreta[i]:
                colores[i] = EstadoCasilla.VERDE
                usadas[i]  = True

        # Contar cuántas veces aparece cada letra en la secreta
        frecuencia_secreta: Dict[str, int] = {}
        for c in secreta:
            frecuencia_secreta[c] = frecuencia_secreta.get(c, 0) + 1

        # Pasada 2: letras presentes pero en posición incorrecta
        for i, letra in enumerate(intento):
            if colores[i] == EstadoCasilla.VERDE:
                continue
            if letra in secreta:
                # ¿La letra aparece más de una vez en la secreta?
                if frecuencia_secreta.get(letra, 0) > 1:
                    colores[i] = EstadoCasilla.AZUL
                else:
                    colores[i] = EstadoCasilla.GRIS

        return colores

    # ─── Registro de intentos ────────────────────────────────────────────────
    def registrar_intento_humano(self, intento: str) -> Optional[ResultadoTurno]:
        resultado = self.evaluar_intento(intento, es_ia=False)
        if resultado:
            self.humano_envio = True
            self.intento_humano_pendiente = intento
        return resultado

    def registrar_intento_ia(self, intento: str,
                              historial: "HistorialIA" = None):
        resultado = self.evaluar_intento(intento, es_ia=True)
        if resultado:
            self.ia_envio = True
            self.intento_ia_pendiente = intento
            if historial:
                self.historial_ia.append(historial)
        return resultado

    # ─── Avance de turno ────────────────────────────────────────────────────
    def avanzar_turno(self):
        # Errores: solo si no ganó en este turno
        if not self.humano.gano:
            self.humano.errores += 1
        if not self.ia.gano:
            self.ia.errores += 1

        self.turno_actual += 1
        self.humano_envio = False
        self.ia_envio     = False
        self.intento_humano_pendiente = ""
        self.intento_ia_pendiente     = ""

        # Nivel 1: revelar siguiente letra al subir de turno
        if self.nivel == "nivel1" and self.turno_actual < self.MAX_TURNOS:
            self._revelar_siguiente_letra()

        # Fin si alguien ganó
        if self.humano.gano or self.ia.gano:
            if not self.humano.gano:
                self.humano.perdio = True
            if not self.ia.gano:
                self.ia.perdio = True
            self.estado = "finalizado"
        elif self.turno_actual >= self.MAX_TURNOS:
            self.humano.perdio = True
            self.ia.perdio     = True
            self.estado        = "finalizado"

    # ─── Utilidades ──────────────────────────────────────────────────────────
    def get_categorias(self) -> List[Dict]:
        return [
            {"key": k, "nombre": v.get("nombre_display", k.title()),
             "emoji": v.get("emoji", "📚"), "total": v.get("total", 0)}
            for k, v in self.dataset["categorias"].items()
        ]

    def get_ganador(self) -> str:
        h, m = self.humano.gano, self.ia.gano
        if h and m:
            if len(self.humano.intentos) < len(self.ia.intentos): return "humano"
            if len(self.ia.intentos) < len(self.humano.intentos): return "ia"
            return "empate"
        if h: return "humano"
        if m: return "ia"
        return "ninguno"

    def get_letras_ia_por_color(self) -> Dict[str, List[str]]:
        """
        Para nivel 2: devuelve letras clasificadas según el historial de la IA.
          verdes    → letra y posición confirmadas
          grises    → letra existe, posición incorrecta
          azules    → letra existe más de una vez
          descartadas → no existen
        """
        verdes      = {}  # pos -> letra
        grises      = set()
        azules      = set()
        descartadas = set()
        for fb, intento in zip(self.ia.feedbacks, self.ia.intentos):
            for i, (color, letra) in enumerate(zip(fb, intento)):
                l = letra.lower()
                if color == EstadoCasilla.VERDE:
                    verdes[i] = l
                elif color == EstadoCasilla.GRIS:
                    grises.add(l)
                elif color == EstadoCasilla.AZUL:
                    azules.add(l)
                elif color == EstadoCasilla.OSCURO:
                    descartadas.add(l)
        return {
            "verdes":      verdes,
            "grises":      list(grises),
            "azules":      list(azules),
            "descartadas": list(descartadas),
        }

    # Nivel 1 compat
    def get_letras_pista_ia(self) -> List[str]:
        pistas = set()
        for fb, intento in zip(self.ia.feedbacks, self.ia.intentos):
            for color, letra in zip(fb, intento):
                if color in (EstadoCasilla.GRIS, EstadoCasilla.AZUL):
                    pistas.add(letra.lower())
        return list(pistas)

    def get_letras_descartadas_ia(self) -> List[str]:
        desc = set()
        for fb, intento in zip(self.ia.feedbacks, self.ia.intentos):
            for color, letra in zip(fb, intento):
                if color == EstadoCasilla.OSCURO:
                    desc.add(letra.lower())
        return list(desc)

    def is_game_over(self) -> bool:
        return self.estado == "finalizado"

    def turno_str(self) -> str:
        return f"{self.turno_actual + 1}/{self.MAX_TURNOS}"