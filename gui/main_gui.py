"""
Duelo de Palabras — GUI Principal
Estética: Alto's Odyssey — cielo nocturno con gradientes índigo/azul/púrpura,
siluetas en capas, acento carmesí, teoría del color análoga fría + complementario cálido.
"""

import os, sys, time, random, threading, tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Callable
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juego.logica import GestorJuego, EstadoCasilla, HistorialIA
from juego.agente_ia import AgenteIA

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "dataset", "palabras_es.json")

# ── Paleta: Análogos fríos (índigo→azul→cian) + Complementario cálido (carmesí) ──
C = {
    "bg":         "#0D1B2A",
    "bg2":        "#1A2744",
    "bg3":        "#243356",
    "panel":      "#162035",
    "carta":      "#1E2D45",
    "silueta":    "#0A1520",
    "indigo":     "#4A6FA5",
    "cielo":      "#7B9EC4",
    "aurora":     "#9BB5D6",
    "estrella":   "#D4E5F7",
    "carmesi":    "#0E6E9B", #1
    "carmesi_l":  "#660A0A", #2
    "ambar":      "#E67E22",
    "dorado":     "#F39C12",
    "verde":      "#2ECC71",
    "verde_d":    "#27AE60",
    "gris":       "#4A5568",
    "gris_txt":   "#8FA3BF",
    "rojo":       "#0E6E9B", #3
    "azul_ia":    "#5B9BD5",
    "blanco":     "#EAF2FF",
    "blanco2":    "#B8CDE5",
    "borde":      "#2A3F5F",
    "borde_a":    "#4A6FA5",
    "humano":     "#D4E5F7",
    "ia":         "#5B9BD5",
}

ESTADO_COLOR = {
    EstadoCasilla.VERDE:  ("#2ECC71", "#0A1F0A"),
    EstadoCasilla.GRIS:   ("#4A5568", "#D4E5F7"),
    EstadoCasilla.AZUL:   ("#5B9BD5", "#0A1520"),
    EstadoCasilla.OSCURO: ("#0A1520", "#2A3F5F"),
    EstadoCasilla.VACIO:  ("#1E2D45", "#4A6FA5"),
    EstadoCasilla.ACTIVO: ("#243356", "#D4E5F7"),
}


class FondoCielo(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, highlightthickness=0, **kw)
        self._estrellas = []
        self._tw = 0
        self._th = 0
        self._fase = 0
        self._anim_id = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        w, h = event.width, event.height
        if w != self._tw or h != self._th:
            self._tw, self._th = w, h
            self._generar_estrellas(w, h)
            self._dibujar(w, h)

    def _generar_estrellas(self, w, h):
        self._estrellas = []
        for _ in range(120):
            x = random.randint(0, w)
            y = random.randint(0, int(h * 0.65))
            r = random.choice([0.8, 1.0, 1.2, 1.5, 2.0])
            parpadeo = random.random()
            self._estrellas.append((x, y, r, parpadeo))

    def _dibujar(self, w, h):
        self.delete("all")
        if w < 2 or h < 2:
            return
        bandas = [
            (0.00, "#0A1020"), (0.25, "#0D1B3A"),
            (0.50, "#122145"), (0.70, "#1A2E55"),
            (0.85, "#243258"), (1.00, "#1A2744"),
        ]
        pasos = 80
        for i in range(pasos):
            t0 = i / pasos
            t1 = (i + 1) / pasos
            y0 = int(t0 * h)
            y1 = int(t1 * h)
            col = self._interp_multi(t0, bandas)
            self.create_rectangle(0, y0, w, y1, fill=col, outline="")
        self._glow_horizonte(w, h)
        fase = self._fase
        for (x, y, r, parpadeo) in self._estrellas:
            alpha_val = 0.5 + 0.5 * math.sin(fase * 2 + parpadeo * 6.28)
            brillo = int(200 + 55 * alpha_val)
            col_e = "#{:02x}{:02x}{:02x}".format(brillo, brillo, min(255, brillo+20))
            self.create_oval(x-r, y-r, x+r, y+r, fill=col_e, outline="")
        self._dibujar_montanas(w, h)

    def _glow_horizonte(self, w, h):
        hy = int(h * 0.55)
        for i in range(20):
            alpha = (20 - i) / 20
            r_c = int(80 + 20 * alpha)
            g_c = int(40 + 10 * alpha)
            b_c = int(100 + 30 * alpha)
            col = "#{:02x}{:02x}{:02x}".format(r_c, g_c, b_c)
            spread = int(w * 0.25 * alpha)
            cx = w // 2
            self.create_oval(cx - spread, hy - i*3, cx + spread, hy + i*3, fill=col, outline="")

    def _dibujar_montanas(self, w, h):
        self._montanas_capa(w, h, 0.45, 0.65, "#1E3358", picos=7, irr=0.18)
        self._montanas_capa(w, h, 0.55, 0.75, "#162840", picos=5, irr=0.22)
        self._montanas_capa(w, h, 0.70, 1.02, "#0A1520", picos=3, irr=0.12)

    def _montanas_capa(self, w, h, y_min, y_max, color, picos, irr):
        pts = [0, h]
        ancho_pico = w // picos
        for i in range(picos + 1):
            x = int(i * ancho_pico)
            variacion = random.uniform(-irr, irr) if i > 0 else 0
            y_pico = int(h * (y_min + variacion))
            y_base = int(h * y_max)
            if i < picos:
                x_pico = x + ancho_pico // 2
                pts += [x, y_base, x_pico, y_pico]
            else:
                pts += [x, y_base]
        pts += [w, h]
        self.create_polygon(pts, fill=color, outline="", smooth=True)

    def _interp_multi(self, t, bandas):
        for i in range(len(bandas) - 1):
            t0, c0 = bandas[i]
            t1, c1 = bandas[i+1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                return self._mezclar(c0, c1, f)
        return bandas[-1][1]

    def _mezclar(self, c1, c2, t):
        r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        r = int(r1 + (r2-r1)*t)
        g = int(g1 + (g2-g1)*t)
        b = int(b1 + (b2-b1)*t)
        return "#{:02x}{:02x}{:02x}".format(r, g, b)

    def iniciar_animacion(self, widget):
        def tick():
            self._fase += 0.04
            w, h = self._tw, self._th
            if w > 2 and h > 2:
                self._dibujar(w, h)
            self._anim_id = widget.after(80, tick)
        tick()

    def detener_animacion(self):
        if self._anim_id:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass


class Casilla(tk.Canvas):
    SZ = 56; R = 8

    def __init__(self, parent, **kw):
        super().__init__(parent, width=self.SZ, height=self.SZ,
                         bg=C["panel"], highlightthickness=0, **kw)
        self.letra  = ""
        self.estado = EstadoCasilla.VACIO
        self._draw()

    def _draw(self):
        self.delete("all")
        bg_, fg_ = ESTADO_COLOR[self.estado]
        sz = self.SZ
        self._rrect(3, 3, sz-1, sz-1, self.R, fill="#050A10", outline="")
        borde = {
            EstadoCasilla.ACTIVO: C["aurora"],
            EstadoCasilla.VERDE:  C["verde"],
            EstadoCasilla.GRIS:   C["gris"],
            EstadoCasilla.AZUL:   C["azul_ia"],
        }.get(self.estado, C["borde"])
        self._rrect(0, 0, sz-4, sz-4, self.R, fill=bg_, outline=borde, width=2)
        if self.estado in (EstadoCasilla.ACTIVO, EstadoCasilla.VERDE):
            # Reemplazo de color inválido #FFFFFF14 por un gris muy claro sólido
            self._rrect(2, 2, sz-6, 14, 4, fill="#E2E8F0", outline="")
        if self.letra:
            self.create_text((sz-4)//2, (sz-4)//2, text=self.letra.upper(),
                             fill=fg_, font=("Courier New", 20, "bold"))

    def _rrect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
               x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
               x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def set_letra(self, letra: str):
        self.letra = letra; self._draw()

    def set_estado(self, estado: EstadoCasilla, letra: str = None, animar=True):
        if letra is not None: self.letra = letra
        self.estado = estado
        if animar:
            self._flip()
        else:
            self._draw()

    def _flip(self):
        pasos = [1.0, 0.6, 0.2, 0.6, 1.0]
        sz = self.SZ
        def paso(i):
            if i < len(pasos):
                self.config(height=max(4, int(sz * pasos[i])))
                self.after(35, lambda: paso(i+1))
            else:
                self.config(height=sz); self._draw()
        paso(0)

    def iluminar_verde(self):
        self.set_estado(EstadoCasilla.VERDE, self.letra, animar=True)


class Tablero(tk.Frame):
    GAP = 5

    def __init__(self, parent, filas=6, cols=5, **kw):
        super().__init__(parent, bg=C["panel"], **kw)
        self.filas = filas; self.cols = cols
        self.casillas: List[List[Casilla]] = []
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self.casillas = []
        for r in range(self.filas):
            row_f = tk.Frame(self, bg=C["panel"])
            fila = []
            for c in range(self.cols):
                cas = Casilla(row_f)
                cas.pack(side=tk.LEFT, padx=self.GAP//2)
                fila.append(cas)
            self.casillas.append(fila)
        self.mostrar_filas_hasta(0)

    def mostrar_filas_hasta(self, max_fila: int):
        for r, fila in enumerate(self.casillas):
            row_frame = fila[0].master
            if r <= max_fila:
                for cas in fila:
                    cas.pack(side=tk.LEFT, padx=self.GAP//2)
                row_frame.pack(pady=self.GAP//2)
            else:
                row_frame.pack_forget()
        self.update_idletasks()

    def mostrar_siguiente_fila_con_animacion(self, fila_actual: int):
        if fila_actual + 1 < len(self.casillas):
            siguiente_fila = fila_actual + 1
            row_frame = self.casillas[siguiente_fila][0].master
            row_frame.pack(pady=self.GAP//2)
            colores_originales = []
            for cas in self.casillas[siguiente_fila]:
                colores_originales.append(cas.cget("bg"))
                cas.config(bg=C["aurora"]); cas._draw()
            def pop_step(step=0):
                if step < 3:
                    color = C["aurora"] if step % 2 == 0 else C["indigo"]
                    for cas in self.casillas[siguiente_fila]:
                        cas.config(bg=color); cas._draw()
                    self.after(80, lambda: pop_step(step+1))
                else:
                    for i, cas in enumerate(self.casillas[siguiente_fila]):
                        cas.config(bg=colores_originales[i]); cas._draw()
                    self.update_idletasks()
            pop_step()

    def reconfigurar(self, cols: int):
        self.cols = cols; self._build()

    def reset(self):
        for fila in self.casillas:
            for cas in fila:
                cas.letra = ""; cas.estado = EstadoCasilla.VACIO; cas._draw()

    def mostrar_intento(self, fila: int, texto: str, reveladas: list):
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(reveladas) and reveladas[col] is not None:
                cas.estado = EstadoCasilla.VERDE; cas.letra = reveladas[col]; cas._draw()
            elif col < len(texto):
                cas.letra = texto[col]; cas.estado = EstadoCasilla.ACTIVO; cas._draw()
            else:
                cas.letra = ""; cas.estado = EstadoCasilla.ACTIVO; cas._draw()

    def mostrar_input_usuario(self, fila: int, texto: str):
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(texto):
                cas.letra = texto[col]; cas.estado = EstadoCasilla.ACTIVO
            else:
                cas.letra = ""; cas.estado = EstadoCasilla.ACTIVO
            cas._draw()

    def mostrar_intento_oculto(self, fila: int, longitud: int, reveladas: list):
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(reveladas) and reveladas[col] is not None:
                cas.letra = reveladas[col]; cas.estado = EstadoCasilla.VERDE; cas._draw()
            else:
                cas.letra = "X"; cas.estado = EstadoCasilla.ACTIVO; cas._draw()

    def revelar(self, fila: int, intento: str, colores: List[EstadoCasilla], oculto=False):
        def rev(col):
            if col < len(colores):
                if oculto and colores[col] != EstadoCasilla.VERDE:
                    letra = "X"
                else:
                    letra = intento[col]
                self.casillas[fila][col].set_estado(colores[col], letra)
                self.after(110, lambda: rev(col+1))
        rev(0)

    def iluminar_victoria(self, fila: int, palabra: str):
        def il(col):
            if col < len(self.casillas[fila]):
                cas = self.casillas[fila][col]
                cas.letra = palabra[col] if col < len(palabra) else ""
                cas.set_estado(EstadoCasilla.VERDE, animar=True)
                self.after(80, lambda: il(col+1))
        il(0)

    def limpiar_activa(self, fila: int, reveladas: list):
        self.mostrar_filas_hasta(fila)
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(reveladas) and reveladas[col] is not None:
                cas.letra = reveladas[col]; cas.estado = EstadoCasilla.VERDE
            else:
                cas.letra = ""; cas.estado = EstadoCasilla.ACTIVO
            cas._draw()

    def limpiar_activa_oculta(self, fila: int, reveladas: list):
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(reveladas) and reveladas[col] is not None:
                cas.letra = reveladas[col]; cas.estado = EstadoCasilla.VERDE; cas._draw()
            else:
                cas.letra = "X"; cas.estado = EstadoCasilla.ACTIVO; cas._draw()


class Ahorcado(tk.Canvas):
    W, H = 110, 140

    def __init__(self, parent, color=C["humano"], **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=C["panel"], highlightthickness=0, **kw)
        self.errores = 0; self.color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        g = C["gris_txt"]
        self.create_line(8, self.H-8, self.W-8, self.H-8, fill=g, width=3, capstyle=tk.ROUND)
        self.create_line(25, self.H-8, 25, 12, fill=g, width=3, capstyle=tk.ROUND)
        self.create_line(25, 12, 72, 12, fill=g, width=3, capstyle=tk.ROUND)
        self.create_line(72, 12, 72, 30, fill=g, width=2, capstyle=tk.ROUND)
        c = self.color
        if self.errores >= 1:
            self.create_oval(57, 30, 87, 60, outline=c, width=3)
            self.create_arc(63, 47, 81, 58, start=0, extent=-180, outline=c, width=2)
        if self.errores >= 2:
            self.create_line(72, 60, 72, 98, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 3:
            self.create_line(72, 70, 52, 88, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 4:
            self.create_line(72, 70, 92, 88, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 5:
            self.create_line(72, 98, 52, 122, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 6:
            self.create_line(72, 98, 92, 122, fill=c, width=3, capstyle=tk.ROUND)
            for dx, ex in [(57,63),(77,83)]:
                self.create_line(dx,36,ex,42,fill=c,width=2)
                self.create_line(ex,36,dx,42,fill=c,width=2)

    def set_errores(self, n: int):
        self.errores = min(6, n); self._draw()

    def reset(self):
        self.errores = 0; self._draw()


class Cronometro(tk.Canvas):
    W, H = 240, 64

    def __init__(self, parent, total=30, on_fin=None, **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=C["bg"], highlightthickness=0, **kw)
        self.total = total; self.restante = total; self.on_fin = on_fin
        self._activo = False; self._tarea = None
        self._draw()

    def _draw(self):
        self.delete("all")
        r = self.restante / self.total
        if r > 0.6:
            color = C["verde"]
        elif r > 0.3:
            color = C["ambar"]
        else:
            color = C["carmesi_l"]
        w, h = self.W, self.H
        bw = int((w-24) * r)
        self._rrect(12, 38, w-12, 54, 7, fill=C["bg2"], outline=C["borde"])
        if bw > 0:
            self._rrect(12, 38, 12+bw, 54, 7, fill=color, outline="")
            if bw > 8:
                # Reemplazo de color inválido #FFFFFF20 por un gris claro sólido
                self._rrect(14, 39, min(12+bw, w-14), 44, 4, fill="#E2E8F0", outline="")
        self.create_text(w//2, 22, text=str(self.restante),
                         font=("Courier New", 24, "bold"), fill=color)
        self.create_text(w//2, 60, text="SEGUNDOS",
                         font=("Courier New", 7, "bold"), fill=C["gris_txt"])

    def _rrect(self, x1,y1,x2,y2,r,**kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def iniciar(self):
        self._activo = True; self.restante = self.total; self._tick()

    def _tick(self):
        if not self._activo: return
        self._draw()
        if self.restante <= 0:
            self._activo = False
            if self.on_fin: self.on_fin()
            return
        self.restante -= 1
        self._tarea = self.after(1000, self._tick)

    def detener(self):
        self._activo = False
        if self._tarea: self.after_cancel(self._tarea)

    def reset(self):
        self.detener(); self.restante = self.total; self._draw()


class PantallaMenu(tk.Frame):
    def __init__(self, parent, on_iniciar: Callable, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.on_iniciar = on_iniciar
        self.cat_var  = tk.StringVar()
        self.lon_var  = tk.IntVar(value=5)
        self.modo_var = tk.StringVar(value="nivel1")
        self._cielo   = None
        self._build()

    def _build(self):
        self._cielo = FondoCielo(self, bg=C["bg"])
        self._cielo.place(relx=0, rely=0, relwidth=1, relheight=1)

        outer = tk.Frame(self, bg=C["bg"])
        outer.place(relx=0.5, rely=0.5, anchor="center")

        titulo_frame = tk.Frame(outer, bg=C["bg"])
        titulo_frame.pack(pady=(0, 4))

        linea = tk.Canvas(titulo_frame, width=40, height=4, bg=C["bg"], highlightthickness=0)
        linea.pack(pady=(0,8))
        linea.create_rectangle(0, 0, 40, 4, fill=C["carmesi"], outline="")

        tk.Label(titulo_frame, text="DUELO DE PALABRAS",
                 font=("Courier New", 32, "bold"),
                 bg=C["bg"], fg=C["blanco"]).pack()
        tk.Label(titulo_frame, text="Humano  \u2694  Máquina Entrenada",
                 font=("Courier New", 12), bg=C["bg"], fg=C["cielo"]).pack(pady=(4,0))

        dot_f = tk.Canvas(titulo_frame, width=120, height=10, bg=C["bg"], highlightthickness=0)
        dot_f.pack(pady=(8,20))
        for i, x in enumerate([20, 40, 60, 80, 100]):
            color = C["carmesi"] if i == 2 else C["indigo"]
            dot_f.create_oval(x-3, 2, x+3, 8, fill=color, outline="")

        panel = tk.Frame(outer, bg=C["bg2"], padx=36, pady=28,
                         highlightbackground=C["borde_a"], highlightthickness=1)
        panel.pack()

        self._label_sec(panel, "\u25b8  CATEGOR\u00cdA  (visible solo para ti)")
        gestor_t = GestorJuego(DATASET_PATH)
        cats = gestor_t.get_categorias()
        self.cat_var.set(cats[0]["key"])
        f_cats = tk.Frame(panel, bg=C["bg2"]); f_cats.pack(fill="x", pady=(6,20))
        self._bots_cat = {}
        for i, cat in enumerate(cats):
            b = self._chip(f_cats, "{} {}".format(cat['emoji'], cat['nombre']),
                           lambda k=cat["key"]: self._sel_cat(k), C["carmesi"], C["bg3"])
            b.grid(row=i//3, column=i%3, padx=3, pady=3, sticky="ew")
            f_cats.columnconfigure(i%3, weight=1)
            self._bots_cat[cat["key"]] = b
        self._sel_cat(cats[0]["key"])

        self._label_sec(panel, "\u25b8  LONGITUD DE PALABRA")
        f_lon = tk.Frame(panel, bg=C["bg2"]); f_lon.pack(fill="x", pady=(6,20))
        self._bots_lon = {}
        for lon in [4, 5, 6]:
            b = self._chip(f_lon, "{} letras".format(lon),
                           lambda l=lon: self._sel_lon(l), C["indigo"], C["bg3"])
            b.pack(side=tk.LEFT, padx=3, expand=True, fill="x")
            self._bots_lon[lon] = b
        self._sel_lon(5)

        self._label_sec(panel, "\u25b8  MODO DE LA IA")
        f_modo = tk.Frame(panel, bg=C["bg2"]); f_modo.pack(fill="x", pady=(6,28))
        self._bots_modo = {}
        modos = [
            ("nivel1", "\U0001f535  Nivel 1 \u2014 GRU", "Letras reveladas de izquierda a derecha"),
            ("nivel2", "\U0001f7e1  Nivel 2 \u2014 MLP", "Sin letras fijas: Wordle completo con colores"),
        ]
        for key, lbl, desc in modos:
            f = tk.Frame(f_modo, bg=C["bg3"], padx=14, pady=10, cursor="hand2",
                         highlightbackground=C["borde"], highlightthickness=1)
            f.pack(side=tk.LEFT, padx=4, expand=True, fill="x")
            tk.Label(f, text=lbl, font=("Courier New",10,"bold"),
                     bg=C["bg3"], fg=C["blanco"]).pack(anchor="w")
            tk.Label(f, text=desc, font=("Courier New",8),
                     bg=C["bg3"], fg=C["gris_txt"]).pack(anchor="w")
            for w in [f]+list(f.winfo_children()):
                w.bind("<Button-1>", lambda e, k=key: self._sel_modo(k))
            self._bots_modo[key] = f
        self._sel_modo("nivel1")

        btn = tk.Canvas(panel, width=280, height=52,
                        bg=C["bg2"], highlightthickness=0, cursor="hand2")
        btn.pack()

        def _draw_btn(hover=False):
            btn.delete("all")
            col = C["carmesi_l"] if hover else C["carmesi"]
            self._rrect_c(btn, 0, 0, 280, 52, 8, fill=col, outline="")
            # Reemplazo de color inválido #FFFFFF22 por un gris claro sólido
            #self._rrect_c(btn, 2, 2, 278, 22, 6, fill="#E2E8F0", outline="")
            btn.create_text(140, 27, text="⚡   INICIAR DUELO",
                            font=("Courier New",14,"bold"), fill=C["blanco"])

        _draw_btn()
        btn.bind("<Enter>", lambda e: _draw_btn(True))
        btn.bind("<Leave>", lambda e: _draw_btn(False))
        btn.bind("<Button-1>", lambda e: self._iniciar())

        #self.after(10, lambda: self._cielo.iniciar_animacion(self))

    def _rrect_c(self, canvas, x1, y1, x2, y2, r, **kw):
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
               x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
               x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        canvas.create_polygon(pts, smooth=True, **kw)

    def _label_sec(self, parent, texto):
        f = tk.Frame(parent, bg=C["bg2"]); f.pack(fill="x")
        tk.Label(f, text=texto, font=("Courier New",9,"bold"),
                 bg=C["bg2"], fg=C["aurora"]).pack(anchor="w")

    def _chip(self, parent, texto, cmd, col_on, col_off):
        b = tk.Label(parent, text=texto, font=("Courier New",10),
                     bg=col_off, fg=C["blanco2"], padx=10, pady=8, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        b._on = col_on; b._off = col_off
        return b

    def _sel_cat(self, key):
        self.cat_var.set(key)
        for k, b in self._bots_cat.items():
            b.config(bg=b._on if k==key else b._off,
                     fg=C["blanco"] if k==key else C["blanco2"])

    def _sel_lon(self, lon):
        self.lon_var.set(lon)
        for l, b in self._bots_lon.items():
            b.config(bg=b._on if l==lon else b._off,
                     fg=C["blanco"] if l==lon else C["blanco2"])

    def _sel_modo(self, key):
        self.modo_var.set(key)
        for k, f in self._bots_modo.items():
            if k == key:
                f.config(bg=C["indigo"], highlightbackground=C["aurora"])
                for ch in f.winfo_children():
                    ch.config(bg=C["indigo"], fg=C["blanco"])
            else:
                f.config(bg=C["bg3"], highlightbackground=C["borde"])
                for ch in f.winfo_children():
                    ch.config(bg=C["bg3"], fg=C["gris_txt"])

    def _iniciar(self):
        if self._cielo:
            self._cielo.detener_animacion()
        self.on_iniciar(self.cat_var.get(), self.lon_var.get(), self.modo_var.get())


class PantallaJuego(tk.Frame):
    def __init__(self, parent, on_volver: Callable, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.on_volver = on_volver
        self.gestor: Optional[GestorJuego] = None
        self.agente: Optional[AgenteIA]    = None
        self._bloqueado    = False
        self._humano_ok    = False
        self._ia_ok        = False
        self._hilo_ia      = None
        self._texto_actual = ""
        self._intentos_ia_reales: List[str] = []
        self._juego_terminado = False
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["bg2"], pady=10,
                       highlightbackground=C["borde"], highlightthickness=1)
        hdr.pack(fill="x")

        btn_v = tk.Label(hdr, text="← Menú", font=("Courier New",10),
                         bg=C["bg2"], fg=C["cielo"], cursor="hand2", padx=14)
        btn_v.pack(side=tk.LEFT)
        btn_v.bind("<Button-1>", lambda e: self._volver())
        btn_v.bind("<Enter>", lambda e: btn_v.config(fg=C["blanco"]))
        btn_v.bind("<Leave>", lambda e: btn_v.config(fg=C["cielo"]))

        self.lbl_turno = tk.Label(hdr, text="Turno 1 / 6",
                                   font=("Courier New",13,"bold"),
                                   bg=C["bg2"], fg=C["blanco"])
        self.lbl_turno.pack(side=tk.LEFT, expand=True)

        lc = tk.Canvas(hdr, width=3, height=24, bg=C["bg2"], highlightthickness=0)
        lc.pack(side=tk.RIGHT, padx=(0,6))
        lc.create_rectangle(0,0,3,24, fill=C["carmesi"], outline="")

        self.lbl_cat = tk.Label(hdr, text="", font=("Courier New",10),
                                 bg=C["bg2"], fg=C["aurora"], padx=10)
        self.lbl_cat.pack(side=tk.RIGHT)

        f_crono = tk.Frame(self, bg=C["bg"]); f_crono.pack(pady=6)
        self.crono = Cronometro(f_crono, total=30, on_fin=self._tiempo_agotado)
        self.crono.pack()

        self.lbl_pista = tk.Label(self, text="", font=("Courier New",11,"bold"),
                                   bg=C["bg"], fg=C["aurora"])
        self.lbl_pista.pack(pady=(0,4))

        self.area = tk.Frame(self, bg=C["bg"])
        self.area.pack(fill="both", expand=True, padx=12, pady=4)
        self.area.columnconfigure(0, weight=1, uniform="col")
        self.area.columnconfigure(2, weight=1, uniform="col")
        self.area.columnconfigure(1, weight=0)

        self.p_humano = self._mk_panel(self.area, "👤   TÚ", C["humano"], es_humano=True)
        self.p_humano.grid(row=0, column=0, sticky="nsew", padx=(0,6))

        sep_f = tk.Frame(self.area, bg=C["bg"])
        sep_f.grid(row=0, column=1, sticky="ns", pady=16)
        sep_c = tk.Canvas(sep_f, width=2, bg=C["bg"], highlightthickness=0)
        sep_c.pack(fill="y", expand=True)
        sep_c.bind("<Configure>", lambda e: [sep_c.delete("all"),
                   sep_c.create_rectangle(0,0,2,e.height, fill=C["carmesi"], outline="")])

        self.p_ia = self._mk_panel(self.area, "🤖   IA", C["ia"], es_humano=False)
        self.p_ia.grid(row=0, column=2, sticky="nsew", padx=(6,0))

        f_inp = tk.Frame(self, bg=C["bg2"],
                         highlightbackground=C["borde"], highlightthickness=1)
        f_inp.pack(fill="x", padx=20, pady=8)
        inp_inner = tk.Frame(f_inp, bg=C["bg2"], pady=8, padx=16)
        inp_inner.pack(fill="x")
        inp_inner.columnconfigure(0, weight=1)

        self.evar = tk.StringVar()
        self.entry = tk.Entry(inp_inner, textvariable=self.evar,
                              font=("Courier New",18,"bold"),
                              bg=C["bg3"], fg=C["blanco"],
                              insertbackground=C["aurora"], relief="flat",
                              highlightthickness=1,
                              highlightcolor=C["aurora"],
                              highlightbackground=C["borde"])
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0,10), ipady=4)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda e: self._enviar())

        self.btn_env = tk.Canvas(inp_inner, width=120, height=40,
                                  bg=C["bg2"], highlightthickness=0, cursor="hand2")
        self.btn_env.grid(row=0, column=1)
        self._draw_btn_env(activo=True)
        self.btn_env.bind("<Button-1>", lambda e: self._enviar())
        self.btn_env.bind("<Enter>", lambda e: self._draw_btn_env(activo=True, hover=True))
        self.btn_env.bind("<Leave>", lambda e: self._draw_btn_env(activo=True, hover=False))

        self.lbl_estado = tk.Label(self, text="", font=("Courier New",10),
                                    bg=C["bg"], fg=C["gris_txt"])
        self.lbl_estado.pack(pady=2)

        self.bind_all("<KeyPress>", self._redirigir_tecla)

    def _draw_btn_env(self, activo=True, hover=False, gris=False):
        self.btn_env.delete("all")
        if gris:
            col = C["borde"]; fg = C["gris_txt"]
        elif hover:
            col = C["carmesi_l"]; fg = C["blanco"]
        else:
            col = C["carmesi"]; fg = C["blanco"]
        pts = [8,0,112,0,120,0,120,8,120,32,120,40,112,40,8,40,0,40,0,32,0,8,0,0]
        self.btn_env.create_polygon(pts, smooth=True, fill=col, outline="")
        self.btn_env.create_text(60, 21, text="ENVIAR →",
                                  font=("Courier New",10,"bold"), fill=fg)

    def _mk_panel(self, parent, titulo, color, es_humano) -> tk.Frame:
        panel = tk.Frame(parent, bg=C["panel"], padx=14, pady=14,
                         highlightbackground=C["borde"], highlightthickness=1)
        hdr_f = tk.Frame(panel, bg=C["panel"])
        hdr_f.pack(fill="x", pady=(0,8))
        ind = tk.Canvas(hdr_f, width=4, height=28, bg=C["panel"], highlightthickness=0)
        ind.pack(side=tk.LEFT, padx=(0,8))
        ind.create_rectangle(0,0,4,28, fill=color, outline="")
        tk.Label(hdr_f, text=titulo, font=("Courier New",13,"bold"),
                 bg=C["panel"], fg=color).pack(side=tk.LEFT)
        ahorcado = Ahorcado(panel, color=color)
        ahorcado.pack()
        tablero = Tablero(panel, filas=6, cols=5)
        tablero.pack(pady=6)
        lbl_env = tk.Label(panel, text="", font=("Courier New",9),
                            bg=C["panel"], fg=C["verde"])
        lbl_env.pack()
        panel._ahorcado  = ahorcado
        panel._tablero   = tablero
        panel._lbl_env   = lbl_env
        panel._color     = color
        panel._es_humano = es_humano
        return panel

    def iniciar(self, categoria: str, longitud: int, modo: str):
        self.gestor = GestorJuego(DATASET_PATH)
        self.agente = AgenteIA(DATASET_PATH, nivel=modo)
        self._intentos_ia_reales = []
        self._juego_terminado = False
        palabra = self.gestor.iniciar_partida(categoria, longitud, nivel=modo)
        print("[DEBUG] Palabra secreta: {}".format(palabra))
        self.p_humano._tablero.reconfigurar(longitud)
        self.p_ia._tablero.reconfigurar(longitud)
        self.p_humano._tablero.mostrar_filas_hasta(0)
        self.p_ia._tablero.mostrar_filas_hasta(0)
        self.p_humano._ahorcado.reset()
        self.p_ia._ahorcado.reset()
        cats = self.gestor.get_categorias()
        cat_info = next((c for c in cats if c["key"]==categoria), None)
        if cat_info:
            self.lbl_pista.config(text="▸  {} {}".format(cat_info['emoji'], cat_info['nombre']))
            self.lbl_cat.config(text="{} {}".format(cat_info['emoji'], cat_info['nombre']))
        self._prep_turno()
        self.crono.iniciar()
        self._lanzar_ia()

    def _prep_turno(self):
        t = self.gestor.turno_actual
        self.lbl_turno.config(text="Turno {} / 6".format(t+1))
        self._bloqueado    = False
        self._humano_ok    = False
        self._ia_ok        = False
        self._texto_actual = ""
        texto_inicial = []
        for i, letra in enumerate(self.gestor.letras_reveladas):
            if letra is not None:
                texto_inicial.append(letra)
            else:
                texto_inicial.append("")   # espacio vacío para las no reveladas
        self.evar.set(''.join(texto_inicial))
        self._texto_actual = texto_inicial
        self.entry.config(state="normal")
        self._draw_btn_env(activo=True)
        self.entry.focus()
        if t > 0 and t <= self.p_humano._tablero.filas:
            self.p_humano._tablero.mostrar_siguiente_fila_con_animacion(t-1)
            self.p_ia._tablero.mostrar_siguiente_fila_con_animacion(t-1)
        else:
            self.p_humano._tablero.mostrar_filas_hasta(t)
            self.p_ia._tablero.mostrar_filas_hasta(t)
        self.p_humano._lbl_env.config(text="")
        self.p_ia._lbl_env.config(text="🤖 Pensando...")
        self.lbl_estado.config(text="⏱  Escribe tu palabra y presiona ENVIAR", fg=C["gris_txt"])
        rev = self.gestor.letras_reveladas
        self.p_humano._tablero.limpiar_activa(t, rev)
        self.p_ia._tablero.limpiar_activa_oculta(t, rev)
        if self.gestor.humano.gano:
            self._humano_ok = True
            self.entry.config(state="disabled")
            self._draw_btn_env(gris=True)
            self.p_humano._lbl_env.config(text="✅ ¡Ya adivinaste!")
            palabra = self.gestor.palabra_secreta
            for col, cas in enumerate(self.p_humano._tablero.casillas[t]):
                cas.set_estado(EstadoCasilla.VERDE, palabra[col], animar=False)
        if self.gestor.ia.gano:
            palabra = self.gestor.palabra_secreta
            for col, cas in enumerate(self.p_ia._tablero.casillas[t]):
                cas.set_estado(EstadoCasilla.VERDE, palabra[col], animar=False)

    def _on_key(self, event):
        if self._bloqueado: return
        texto = self.evar.get().upper()
        reveladas = self.gestor.letras_reveladas
        texto = ''.join(c for c in texto if c.isalpha())
        nuevo_texto = []
        for i, letra_revelada in enumerate(reveladas):
            if letra_revelada is not None:
                nuevo_texto.append(letra_revelada)
            elif i < len(texto):
                nuevo_texto.append(texto[i])
            else:
                nuevo_texto.append("")
        texto_final = ''.join(nuevo_texto)
        lon = self.gestor.longitud_palabra
        texto_final = texto_final[:lon]
        self.evar.set(texto_final)
        self._texto_actual = texto_final
        t = self.gestor.turno_actual
        self.p_humano._tablero.mostrar_input_usuario(t, texto_final)

    def _enviar(self):
        if self._bloqueado or self._humano_ok: return
        intento = self.evar.get().upper()
        lon = self.gestor.longitud_palabra
        reveladas = self.gestor.letras_reveladas
        intento_completo = []
        for i in range(lon):
            if reveladas[i] is not None:
                intento_completo.append(reveladas[i])
            elif i < len(intento) and intento[i]:
                intento_completo.append(intento[i])
            else:
                intento_completo.append("")
        intento = ''.join(intento_completo)
        if len(intento) != lon or not all(c.isalpha() for c in intento):
            self.lbl_estado.config(text="⚠  Completa todas las letras de la palabra", fg=C["carmesi_l"])
            return
        resultado = self.gestor.registrar_intento_humano(intento)
        if resultado is None: return
        self._humano_ok = True
        self.entry.config(state="disabled")
        self._draw_btn_env(gris=True)
        self.p_humano._lbl_env.config(text="✅ Enviado")
        if self._ia_ok:
            self._cerrar_turno()
        else:
            self.lbl_estado.config(text="⏳ Esperando a la IA…", fg=C["gris_txt"])

    def _lanzar_ia(self):
        if not self.gestor or not self.agente: return
        if self.gestor.ia.gano:
            self._ia_ok = True
            self.p_ia._lbl_env.config(text="✅ ¡IA ya adivinó!")
        else:
            self._hilo_ia = self.agente.pensar_async(self.gestor, self._cb_ia)

    def _cb_ia(self, palabra: str, historial: HistorialIA):
        self.after(0, lambda: self._proc_ia(palabra, historial))

    def _proc_ia(self, palabra: str, historial: HistorialIA):
        if self._juego_terminado: return
        self.gestor.registrar_intento_ia(palabra, historial)
        self._intentos_ia_reales.append(palabra)
        self._ia_ok = True
        self.p_ia._lbl_env.config(text="🤖 Listo")
        if self._humano_ok:
            self._cerrar_turno()

    def _tiempo_agotado(self):
        if not self._humano_ok:
            intento = self.evar.get().upper()
            if len(intento) == self.gestor.longitud_palabra:
                self._enviar()
            else:
                self._humano_ok = True
                self.entry.config(state="disabled")
                self.p_humano._lbl_env.config(text="⌛ Tiempo agotado")
        if not self._ia_ok:
            self.lbl_estado.config(text="⏳ Esperando a la IA…", fg=C["ambar"])
            self._esperar_ia(0)
        else:
            self._cerrar_turno()

    def _esperar_ia(self, n: int):
        if self._ia_ok:
            self._cerrar_turno()
        elif n < 30:
            self.after(1000, lambda: self._esperar_ia(n+1))
        else:
            self._cerrar_turno()

    def _cerrar_turno(self):
        if self._bloqueado: return
        self._bloqueado = True
        self.crono.detener()
        t = self.gestor.turno_actual
        if self.gestor.humano.feedbacks and not self.gestor.humano.gano:
            fb_h  = self.gestor.humano.feedbacks[-1]
            int_h = self.gestor.humano.intentos[-1]
            self.p_humano._tablero.revelar(t, int_h, fb_h, oculto=False)
        elif self.gestor.humano.gano:
            palabra = self.gestor.palabra_secreta
            self.p_humano._tablero.iluminar_victoria(t, palabra)
        if self.gestor.ia.feedbacks and not self.gestor.ia.gano:
            fb_ia  = self.gestor.ia.feedbacks[-1]
            int_ia = self.gestor.ia.intentos[-1]
            self.p_ia._tablero.revelar(t, int_ia, fb_ia, oculto=True)
        elif self.gestor.ia.gano:
            palabra = self.gestor.palabra_secreta
            self.p_ia._tablero.iluminar_victoria(t, palabra)
        self.gestor.avanzar_turno()
        self.p_humano._ahorcado.set_errores(self.gestor.humano.errores)
        self.p_ia._ahorcado.set_errores(self.gestor.ia.errores)
        delay = 1600
        if self.gestor.is_game_over():
            self.after(delay + 600, self._resultado_final)
        else:
            self.after(delay, self._sig_turno)

    def _sig_turno(self):
        self._prep_turno()
        self.crono.iniciar()
        self._lanzar_ia()

    def _resultado_final(self):
        self._juego_terminado = True
        ganador = self.gestor.get_ganador()
        palabra = self.gestor.palabra_secreta
        ven = tk.Toplevel(self)
        ven.title("Resultado Final")
        ven.configure(bg=C["bg"])
        ven.geometry("540x460")
        ven.resizable(False, False)
        ven.grab_set()
        ven.focus_force()
        bg_c = tk.Canvas(ven, bg=C["bg"], highlightthickness=0)
        bg_c.place(relx=0, rely=0, relwidth=1, relheight=1)
        bg_c.create_rectangle(0, 0, 540, 230, fill=C["bg2"], outline="")
        bg_c.create_rectangle(0, 230, 540, 460, fill=C["bg"], outline="")
        f = tk.Frame(ven, bg=C["bg2"])
        f.place(relx=0.5, rely=0.5, anchor="center")
        if ganador == "humano":
            emo, tit, col = "🏆", "¡GANASTE!", C["dorado"]
        elif ganador == "ia":
            emo, tit, col = "🤖", "LA IA GANÓ", C["azul_ia"]
        elif ganador == "empate":
            emo, tit, col = "🤝", "¡EMPATE!", C["verde"]
        else:
            emo, tit, col = "💀", "NADIE GANÓ", C["carmesi_l"]
        tk.Label(f, text=emo, font=("Courier New",52), bg=C["bg2"], fg=col).pack(pady=(10,0))
        lc = tk.Canvas(f, width=200, height=3, bg=C["bg2"], highlightthickness=0)
        lc.pack(pady=4)
        lc.create_rectangle(0,0,200,3, fill=col, outline="")
        tk.Label(f, text=tit, font=("Courier New",26,"bold"), bg=C["bg2"], fg=col).pack(pady=4)
        tk.Label(f, text="La palabra era:  {}".format(palabra.upper()),
                 font=("Courier New",14), bg=C["bg2"], fg=C["aurora"]).pack(pady=8)
        stats = tk.Frame(f, bg=C["carta"],
                         highlightbackground=C["borde"], highlightthickness=1,
                         padx=20, pady=12)
        stats.pack(fill="x", pady=8, padx=20)
        h_n = len(self.gestor.humano.intentos)
        ia_n = len(self.gestor.ia.intentos)
        tk.Label(stats,
                 text="👤  Tú: {} ({} {})".format(
                     '✅ Acertó' if self.gestor.humano.gano else '❌ Falló',
                     h_n, 'intento' if h_n==1 else 'intentos'),
                 font=("Courier New",11), bg=C["carta"], fg=C["humano"]).pack(anchor="w")
        tk.Label(stats,
                 text="🤖  IA: {} ({} {})".format(
                     '✅ Acertó' if self.gestor.ia.gano else '❌ Falló',
                     ia_n, 'intento' if ia_n==1 else 'intentos'),
                 font=("Courier New",11), bg=C["carta"], fg=C["ia"]).pack(anchor="w")
        bf = tk.Frame(f, bg=C["bg2"]); bf.pack(pady=14)
        def _btn(parent, texto, bg, fg, cmd):
            b = tk.Label(parent, text=texto, font=("Courier New",10,"bold"),
                         bg=bg, fg=fg, padx=14, pady=9, cursor="hand2")
            b.pack(side=tk.LEFT, padx=4)
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>", lambda e: b.config(bg=C["indigo"]))
            b.bind("<Leave>", lambda e: b.config(bg=bg))
            return b
        _btn(bf, "🔍 Historial IA", C["bg3"], C["blanco"], self._ver_historial_ia_full)
        _btn(bf, "▶ Nueva partida", C["carmesi"], C["blanco"], lambda: [ven.destroy(), self._volver()])
        _btn(bf, "⇐ Menú", C["borde"], C["blanco2"], lambda: [ven.destroy(), self._volver()])

    def _ver_historial_ia(self):
        if not self._juego_terminado:
            messagebox.showinfo("Historial IA", "El historial de la IA se revela\nal terminar la partida.")
            return
        self._ver_historial_ia_full()

    def _ver_historial_ia_full(self):
        ven = tk.Toplevel(self)
        ven.title("🤖 Predicciones de la IA")
        ven.configure(bg=C["bg"])
        ven.geometry("640x540")
        ven.focus_force()
        tk.Label(ven, text="🧠  Historial de Predicciones de la IA",
                 font=("Courier New",13,"bold"), bg=C["bg"], fg=C["azul_ia"]).pack(pady=12)
        canvas = tk.Canvas(ven, bg=C["bg"], highlightthickness=0)
        sb = tk.Scrollbar(ven, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        fs = tk.Frame(canvas, bg=C["bg"])
        canvas.create_window((0,0), window=fs, anchor="nw")
        for h in self.gestor.historial_ia:
            card = tk.Frame(fs, bg=C["carta"],
                            highlightbackground=C["borde"], highlightthickness=1,
                            padx=14, pady=10)
            card.pack(fill="x", padx=12, pady=4)
            tk.Label(card, text="Turno {}".format(h.turno+1),
                     font=("Courier New",12,"bold"), bg=C["carta"], fg=C["azul_ia"]).pack(anchor="w")
            tk.Label(card, text="Patrón: {}  |  Pistas grises: {}  |  {:.1f}ms".format(h.patron, h.letras_pista, h.tiempo_ms),
                     font=("Courier New",8), bg=C["carta"], fg=C["gris_txt"]).pack(anchor="w")
            tk.Label(card, text="✅ Seleccionó: {}".format(h.seleccionada),
                     font=("Courier New",11,"bold"), bg=C["carta"], fg=C["verde"]).pack(anchor="w", pady=(3,0))
            if h.candidatos:
                tops = "  ".join("{}({:.2f})".format(p,prob) for p,prob in h.candidatos[:3])
                tk.Label(card, text="Top: {}".format(tops), font=("Courier New",8),
                         bg=C["carta"], fg=C["cielo"]).pack(anchor="w")
        fs.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _volver(self):
        self.crono.detener()
        self.on_volver()

    def _redirigir_tecla(self, event):
        if not self.gestor or self._bloqueado or self._humano_ok: return
        if event.keysym in ("Return","Tab","Escape","BackSpace",
                             "Shift_L","Shift_R","Control_L","Control_R",
                             "Alt_L","Alt_R","Super_L","Super_R",
                             "caps","Left","Right","Up","Down",
                             "Delete","Home","End","Prior","Next"):
            if event.keysym == "BackSpace":
                texto = self.evar.get()
                self.evar.set(texto[:-1])
                self._on_key(event)
            return
        if event.char and event.char.isprintable() and event.char.isalpha():
            self.entry.focus()
            texto_actual = self.evar.get()
            lon = self.gestor.longitud_palabra if self.gestor else 5
            if len(texto_actual) < lon:
                self.evar.set(texto_actual + event.char)
                self._on_key(event)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Duelo de Palabras ⚔")
        self.configure(bg=C["bg"])
        self.minsize(860, 680)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(1100, sw - 80)
        h  = min(800,  sh - 80)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry("{}x{}+{}+{}".format(w, h, x, y))
        self.resizable(True, True)
        self._actual = None
        self._menu  = PantallaMenu(self, on_iniciar=self._iniciar)
        self._juego = PantallaJuego(self, on_volver=self._ir_menu)
        self._ir_menu()

    def _ir_menu(self):
        if self._actual: self._actual.pack_forget()
        self._menu.pack(fill="both", expand=True)
        self._actual = self._menu

    def _iniciar(self, cat, lon, modo):
        if self._actual: self._actual.pack_forget()
        self._juego.pack(fill="both", expand=True)
        self._actual = self._juego
        self._juego.iniciar(cat, lon, modo)


if __name__ == "__main__":
    app = App()
    app.mainloop()