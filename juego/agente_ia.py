"""
Agente de Inteligencia Artificial para Duelo de Palabras.

· Nivel 1 (GRU): recibe SOLO el patrón de letras reveladas de izquierda
  a derecha. Nunca recibe información de colores previos.

· Nivel 2 (MLP): recibe el estado completo de pistas acumuladas:
  verdes (pos exacta), grises (existe, pos incorrecta), azules (existe,
  letra doble), descartadas (no existen). No recibe prefijo revelado.
"""

import os
import time
import random
import threading
from typing import List, Tuple, Callable, Optional, Dict

from juego.logica import GestorJuego, HistorialIA, EstadoCasilla


class AgenteIA:
    DELAY_MIN = 2.0   # segundos mínimos antes de responder (simula "pensamiento")
    DELAY_MAX = 8.0   # segundos máximos

    def __init__(self, dataset_path: str, nivel: str = "nivel1"):
        self.nivel    = nivel
        self.inferencia = None
        self._inicializar(dataset_path)

    def _inicializar(self, dataset_path: str):
        try:
            from model.gru import InferenciaGRU
            self.inferencia = InferenciaGRU(dataset_path)
            if self.nivel == "nivel1" and self.inferencia.disponible_n1:
                print("🤖 IA Nivel 1: modelo GRU cargado.")
            elif self.nivel == "nivel2" and self.inferencia.disponible_n2:
                print("🤖 IA Nivel 2: modelo MLP cargado.")
            else:
                print(f"🤖 IA {self.nivel}: modo heurístico (sin modelo entrenado).")
        except Exception as e:
            print(f"🤖 IA: fallback estadístico ({e}).")

    def pensar_async(self, gestor: GestorJuego,
                     callback: Callable[[str, HistorialIA], None]):
        hilo = threading.Thread(
            target=self._pensar_y_llamar,
            args=(gestor, callback),
            daemon=True
        )
        hilo.start()
        return hilo

    def _pensar_y_llamar(self, gestor: GestorJuego,
                          callback: Callable[[str, HistorialIA], None]):
        t0    = time.time()
        delay = random.uniform(self.DELAY_MIN, self.DELAY_MAX)

        longitud = gestor.longitud_palabra

        if self.nivel == "nivel1":
            candidatos, patron = self._pensar_nivel1(gestor, longitud)
            pistas_log         = []
        else:
            candidatos, patron, pistas_log = self._pensar_nivel2(gestor, longitud)

        # Filtro duro para nivel 1: respetar el patrón revelado
        if self.nivel == "nivel1":
            candidatos = self._filtrar_patron(candidatos, patron, longitud)

        if not candidatos:
            candidatos = self._emergencia(gestor, longitud)

        t_calc = (time.time() - t0) * 1000

        # Esperar el resto del delay simulado
        restante = delay - (time.time() - t0)
        if restante > 0:
            time.sleep(restante)

        seleccionada = candidatos[0][0].upper() if candidatos else "A" * longitud

        historial = HistorialIA(
            turno        = gestor.turno_actual,
            patron       = patron,
            letras_pista = pistas_log,
            candidatos   = candidatos[:5],
            seleccionada = seleccionada,
            tiempo_ms    = t_calc,
        )
        callback(seleccionada, historial)

    # ── Nivel 1 ───────────────────────────────────────────────────────────────
    def _pensar_nivel1(self, gestor: GestorJuego,
                        longitud: int) -> Tuple[List[Tuple[str, float]], str]:
        """
        Solo usa el patrón de letras reveladas. NUNCA usa colores previos.
        """
        patron = gestor.get_patron_actual()  # ej. "G____"

        if self.inferencia:
            try:
                return self.inferencia.predecir_nivel1(patron, longitud), patron
            except Exception as e:
                print(f"⚠️  Error GRU N1: {e}")

        # Fallback: buscar en vocabulario por patrón
        vocab = self.inferencia.vocab_n1 if self.inferencia else []
        from model.gru import _match_patron
        cands = [(p, 1.0) for p in vocab
                 if len(p) == longitud and _match_patron(p, patron.lower())]
        random.shuffle(cands)
        return cands[:8] or [("a"*longitud, 0.1)], patron

    # ── Nivel 2 ───────────────────────────────────────────────────────────────
    def _pensar_nivel2(self, gestor: GestorJuego,
                        longitud: int) -> Tuple[List[Tuple[str, float]], str, List[str]]:
        """
        Usa el estado completo de pistas acumuladas (verdes/grises/azules/desc).
        Si es el primer turno (sin historial), elige una palabra aleatoria del vocab.
        """
        info = gestor.get_letras_ia_por_color()
        verdes:      Dict[int, str] = info["verdes"]
        grises:      List[str]      = info["grises"]
        azules:      List[str]      = info["azules"]
        descartadas: List[str]      = info["descartadas"]

        pistas_log = grises + azules  # para el historial

        # Turno inicial: no hay pistas → palabra aleatoria
        if not verdes and not grises and not azules and not descartadas:
            vocab = self.inferencia.vocab_n2 if self.inferencia else []
            opts  = [p for p in vocab if len(p) == longitud]
            if opts:
                palabra = random.choice(opts)
                return [(palabra, 1.0)], "inicial", pistas_log

        if self.inferencia:
            try:
                cands = self.inferencia.predecir_nivel2(
                    longitud, verdes, grises, azules, descartadas)
                return cands, str(verdes), pistas_log
            except Exception as e:
                print(f"⚠️  Error MLP N2: {e}")

        # Fallback heurístico
        from model.gru import _cumple_restricciones
        vocab = self.inferencia.vocab_n2 if self.inferencia else []
        cands = [(p, 1.0) for p in vocab
                 if len(p) == longitud and
                    _cumple_restricciones(p, verdes, grises, azules, descartadas)]
        random.shuffle(cands)
        return cands[:8] or [("a"*longitud, 0.1)], str(verdes), pistas_log

    # ── Utilidades ────────────────────────────────────────────────────────────
    def _filtrar_patron(self, candidatos: List[Tuple[str, float]],
                         patron: str, longitud: int) -> List[Tuple[str, float]]:
        from model.gru import _match_patron
        patron_l = patron.lower()
        return [(p, s) for p, s in candidatos
                if len(p) == longitud and _match_patron(p, patron_l)]

    def _emergencia(self, gestor: GestorJuego,
                     longitud: int) -> List[Tuple[str, float]]:
        """Último recurso: buscar en el dataset completo."""
        vocab = set()
        try:
            for cat in gestor.dataset["categorias"].values():
                for p in cat["palabras"]:
                    if p["longitud"] == longitud:
                        vocab.add(p["palabra"].lower())
        except Exception:
            pass
        if self.inferencia:
            for p in (self.inferencia.vocab_n1 + self.inferencia.vocab_n2):
                if len(p) == longitud:
                    vocab.add(p)
        cands = list(vocab)
        random.shuffle(cands)
        return [(p, 0.1) for p in cands[:5]] or [("a"*longitud, 0.0)]