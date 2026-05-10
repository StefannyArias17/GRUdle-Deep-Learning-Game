"""
Agente de Inteligencia Artificial para Duelo de Palabras.
"""

import os
import time
import random
import threading
from typing import List, Tuple, Callable, Optional

from juego.logica import GestorJuego, HistorialIA


class AgenteIA:
    DELAY_MIN  = 2.0
    DELAY_MAX  = 8.0

    def __init__(self, dataset_path: str, modo: str = "cat1"):
        self.modo     = modo
        self.inferencia = None
        self._inicializar_inferencia(dataset_path)

    def _inicializar_inferencia(self, dataset_path: str):
        try:
            from model.gru import InferenciaGRU
            self.inferencia = InferenciaGRU(dataset_path)
            if self.inferencia.disponible:
                print("🤖 Agente IA: modelos GRU cargados correctamente.")
            else:
                print("🤖 Agente IA: usando modo heurístico (GRU no entrenado).")
        except Exception as e:
            print(f"🤖 Agente IA: fallback estadístico activado ({e}).")

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
        t_inicio = time.time()
        delay = random.uniform(self.DELAY_MIN, self.DELAY_MAX)

        patron     = gestor.get_patron_actual()
        longitud   = gestor.longitud_palabra
        pistas     = gestor.get_letras_pista_ia()
        descartadas = gestor.get_letras_descartadas_ia()

        candidatos = self._predecir(patron, longitud, pistas, descartadas)
        t_calculo = (time.time() - t_inicio) * 1000

        tiempo_restante = delay - (time.time() - t_inicio)
        if tiempo_restante > 0:
            time.sleep(tiempo_restante)

        if candidatos:
            seleccionada = candidatos[0][0].upper()
        else:
            seleccionada = self._palabra_aleatoria(longitud, gestor)

        historial = HistorialIA(
            turno       = gestor.turno_actual,
            patron      = patron,
            letras_pista = pistas,
            candidatos  = candidatos,
            seleccionada = seleccionada,
            tiempo_ms   = t_calculo
        )

        callback(seleccionada, historial)

    def _predecir(self, patron: str, longitud: int,
                  letras_pista: List[str],
                  letras_descartadas: List[str]) -> List[Tuple[str, float]]:
        if self.inferencia:
            try:
                if self.modo == "cat2":
                    return self.inferencia.predecir_cat2(
                        patron, longitud, letras_pista, letras_descartadas)
                else:
                    return self.inferencia.predecir_cat1(patron, longitud)
            except Exception as e:
                print(f"⚠️  Error en inferencia GRU: {e}")

        return self._heuristica(patron, longitud, letras_pista, letras_descartadas)

    def _heuristica(self, patron: str, longitud: int,
                    letras_pista: List[str],
                    letras_descartadas: List[str]) -> List[Tuple[str, float]]:
        if self.inferencia:
            vocab = self.inferencia.vocabulario
        else:
            vocab = ["gato", "perro", "mesa", "silla", "libro", "lapiz",
                     "reloj", "bolso", "plato", "sopa", "vino", "copa",
                     "arbol", "prado", "selva", "monte", "valle", "bosque",
                     "azul", "verde", "rojo", "negro", "blanco", "gris"]

        patron_lower      = patron.lower()
        pistas_set        = set(l.lower() for l in letras_pista)
        descartadas_set   = set(l.lower() for l in letras_descartadas)
        candidatos        = []

        for palabra in vocab:
            if len(palabra) != longitud:
                continue

            match = True
            for i, c in enumerate(patron_lower):
                if i >= len(palabra):
                    match = False
                    break
                if c != "_" and c.lower() != palabra[i]:
                    match = False
                    break
            if not match:
                continue

            if any(l in palabra for l in descartadas_set):
                continue

            if not all(l in palabra for l in pistas_set):
                continue

            score = sum(1.0 for l in pistas_set if l in palabra) / max(1, len(pistas_set) + 1)
            candidatos.append((palabra, score))

        if not candidatos:
            candidatos = [(p, 0.3) for p in vocab if len(p) == longitud]

        candidatos.sort(key=lambda x: x[1], reverse=True)
        return candidatos[:5]

    def _palabra_aleatoria(self, longitud: int, gestor: GestorJuego) -> str:
        try:
            opciones = []
            for cat in gestor.dataset["categorias"].values():
                opciones.extend(p["palabra"].upper()
                                for p in cat["palabras"]
                                if p["longitud"] == longitud)
            if opciones:
                return random.choice(opciones)
        except Exception:
            pass
        return ("A" * longitud)[:longitud]
