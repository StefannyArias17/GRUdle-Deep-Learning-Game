"""
Lógica central del juego Duelo de Palabras.
"""

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple


class EstadoCasilla(Enum):
    VACIO  = "vacio"
    VERDE  = "verde"
    GRIS   = "gris"
    OSCURO = "oscuro"
    ACTIVO = "activo"


@dataclass
class ResultadoTurno:
    palabra: str
    colores: List[EstadoCasilla]
    acerto: bool
    tiempo_respuesta: float = 0.0


@dataclass
class EstadoJugador:
    intentos:  List[str]                 = field(default_factory=list)
    feedbacks: List[List[EstadoCasilla]] = field(default_factory=list)
    errores:   int  = 0
    gano:      bool = False
    perdio:    bool = False


@dataclass
class HistorialIA:
    turno: int
    patron: str
    letras_pista: List[str]
    candidatos: List[Tuple[str, float]]
    seleccionada: str
    tiempo_ms: float


class GestorJuego:
    MAX_TURNOS   = 6
    TIEMPO_TURNO = 30

    def __init__(self, dataset_path: str):
        self.dataset = self._cargar_dataset(dataset_path)
        self.estado = "espera"
        self.reset()

    def _cargar_dataset(self, path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reset(self):
        self.turno_actual    = 0
        self.palabra_secreta = ""
        self.categoria       = ""
        self.longitud_palabra = 5
        self.letras_reveladas: List[Optional[str]] = []
        self.humano          = EstadoJugador()
        self.ia              = EstadoJugador()
        self.historial_ia    : List[HistorialIA] = []
        self.estado          = "espera"
        self.humano_envio    = False
        self.ia_envio        = False
        self.intento_humano_pendiente = ""
        self.intento_ia_pendiente     = ""

    def iniciar_partida(self, categoria: str, longitud: int) -> str:
        self.reset()
        self.categoria        = categoria
        self.longitud_palabra = longitud
        self.palabra_secreta  = self._seleccionar_palabra(categoria, longitud)
        self.letras_reveladas = [None] * len(self.palabra_secreta)
        self.estado           = "jugando"
        self._revelar_siguiente_letra()
        return self.palabra_secreta

    def _seleccionar_palabra(self, categoria: str, longitud: int) -> str:
        cat_data = self.dataset["categorias"].get(categoria, {})
        palabras = cat_data.get("palabras", [])
        opciones_alta = [p["palabra"].upper() for p in palabras
                         if p["longitud"] == longitud and p.get("frecuencia", 0) >= 70]
        opciones_todas = [p["palabra"].upper() for p in palabras if p["longitud"] == longitud]
        pool = opciones_alta if opciones_alta else opciones_todas
        if not pool:
            pool = []
            for cat in self.dataset["categorias"].values():
                pool.extend(p["palabra"].upper() for p in cat["palabras"] if p["longitud"] == longitud)
        if not pool:
            pool = ["GATO"] if longitud == 4 else ["PERRO"] if longitud == 5 else ["NUTRIA"]
        return random.choice(pool)

    def _revelar_siguiente_letra(self) -> int:
        for i, letra in enumerate(self.letras_reveladas):
            if letra is None:
                self.letras_reveladas[i] = self.palabra_secreta[i]
                return i
        return -1

    def get_patron_actual(self) -> str:
        return "".join(l if l else "_" for l in self.letras_reveladas)

    def evaluar_intento(self, intento: str, es_ia: bool) -> Optional[ResultadoTurno]:
        if self.estado != "jugando":
            return None
        intento = intento.upper().strip()
        if len(intento) != len(self.palabra_secreta):
            return None

        jugador = self.ia if es_ia else self.humano
        acerto  = (intento == self.palabra_secreta)
        colores: List[EstadoCasilla] = []

        for i, letra in enumerate(intento):
            if self.letras_reveladas[i] is not None:
                colores.append(EstadoCasilla.VERDE)
            elif letra in self.palabra_secreta:
                colores.append(EstadoCasilla.GRIS)
            else:
                colores.append(EstadoCasilla.OSCURO)

        jugador.intentos.append(intento)
        jugador.feedbacks.append(colores)
        if acerto:
            jugador.gano = True

        return ResultadoTurno(intento, colores, acerto)

    def registrar_intento_humano(self, intento: str) -> Optional[ResultadoTurno]:
        resultado = self.evaluar_intento(intento, es_ia=False)
        if resultado:
            self.humano_envio = True
            self.intento_humano_pendiente = intento
        return resultado

    def registrar_intento_ia(self, intento: str, historial: "HistorialIA" = None):
        resultado = self.evaluar_intento(intento, es_ia=True)
        if resultado:
            self.ia_envio = True
            self.intento_ia_pendiente = intento
            if historial:
                self.historial_ia.append(historial)
        return resultado

    def avanzar_turno(self):
        if not self.humano.gano:
            if not self.humano_envio:
                self.humano.errores += 1
            elif self.intento_humano_pendiente != self.palabra_secreta:
                self.humano.errores += 1

        if not self.ia.gano:
            if not self.ia_envio:
                self.ia.errores += 1
            elif self.intento_ia_pendiente != self.palabra_secreta:
                self.ia.errores += 1

        self.turno_actual += 1
        self.humano_envio = False
        self.ia_envio     = False
        self.intento_humano_pendiente = ""
        self.intento_ia_pendiente     = ""

        if self.turno_actual < self.MAX_TURNOS:
            self._revelar_siguiente_letra()

        # Termina SOLO si ambos ganaron
        if self.humano.gano and self.ia.gano:
            self.estado = "finalizado"
            return

        # Termina si se agotaron todos los turnos
        if self.turno_actual >= self.MAX_TURNOS:
            if not self.humano.gano:
                self.humano.perdio = True
            if not self.ia.gano:
                self.ia.perdio = True
            self.estado = "finalizado"

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

    def get_letras_pista_ia(self) -> List[str]:
        pistas = set()
        for fb, intento in zip(self.ia.feedbacks, self.ia.intentos):
            for color, letra in zip(fb, intento):
                if color == EstadoCasilla.GRIS:
                    pistas.add(letra.lower())
        return list(pistas)

    def get_letras_descartadas_ia(self) -> List[str]:
        descartadas = set()
        for fb, intento in zip(self.ia.feedbacks, self.ia.intentos):
            for color, letra in zip(fb, intento):
                if color == EstadoCasilla.OSCURO:
                    descartadas.add(letra.lower())
        return list(descartadas)

    def is_game_over(self) -> bool:
        return self.estado == "finalizado"

    def turno_str(self) -> str:
        return f"{self.turno_actual + 1}/{self.MAX_TURNOS}"
