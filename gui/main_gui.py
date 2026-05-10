"""
Duelo de Palabras — GUI Principal (versión corregida)
Tkinter responsive, dos columnas simétricas, todas las mecánicas del spec.
"""

import os, sys, time, random, threading, tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juego.logica import GestorJuego, EstadoCasilla, HistorialIA
from juego.agente_ia import AgenteIA

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "dataset", "palabras_es.json")

# ── Paleta ────────────────────────────────────────────────────────────────────
C = {
    "bg":        "#0D0D1A",
    "panel":     "#12122A",
    "carta":     "#1A1A35",
    "input":     "#1E1E3A",
    "verde":     "#00E87A",
    "verde_d":   "#00B55F",
    "gris":      "#5B6DA0",
    "oscuro":    "#252545",
    "dorado":    "#FFD700",
    "dorado_d":  "#CC9900",
    "rojo":      "#FF3355",
    "azul":      "#00AAFF",
    "blanco":    "#FFFFFF",
    "gris_txt":  "#7880A0",
    "borde":     "#252550",
    "borde_a":   "#4040A0",
    "humano":    "#FF6B35",
    "ia":        "#00AAFF",
}

ESTADO_COLOR = {
    EstadoCasilla.VERDE:  (C["verde"],  "#000000"),
    EstadoCasilla.GRIS:   (C["gris"],   "#FFFFFF"),
    EstadoCasilla.OSCURO: (C["oscuro"], "#444466"),
    EstadoCasilla.VACIO:  (C["carta"],  "#FFFFFF"),
    EstadoCasilla.ACTIVO: (C["input"],  "#FFFFFF"),
}


# ── Casilla ───────────────────────────────────────────────────────────────────
class Casilla(tk.Canvas):
    SZ = 56; R = 7

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
        self._rrect(2, 2, sz-2, sz-2, self.R, fill="#000000", outline="")
        borde = {EstadoCasilla.ACTIVO: C["borde_a"],
                 EstadoCasilla.VERDE:  C["verde"],
                 EstadoCasilla.GRIS:   C["gris"]}.get(self.estado, C["borde"])
        self._rrect(0, 0, sz-4, sz-4, self.R, fill=bg_, outline=borde, width=2)
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


# ── Tablero ───────────────────────────────────────────────────────────────────
class Tablero(tk.Frame):
    GAP = 4

    def __init__(self, parent, filas=6, cols=5, **kw):
        super().__init__(parent, bg=C["carta"], **kw)
        self.filas = filas; self.cols = cols
        self.casillas: List[List[Casilla]] = []
        self._build()

    def _build(self):
        for w in self.winfo_children(): w.destroy()
        self.casillas = []
        for r in range(self.filas):
            row_f = tk.Frame(self, bg=C["carta"])
            row_f.pack(pady=self.GAP//2)
            fila = []
            for c in range(self.cols):
                cas = Casilla(row_f)
                cas.pack(side=tk.LEFT, padx=self.GAP//2)
                fila.append(cas)
            self.casillas.append(fila)

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

    def mostrar_intento_oculto(self, fila: int, longitud: int, reveladas: list):
        """Para la IA: muestra X en posiciones no reveladas."""
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(reveladas) and reveladas[col] is not None:
                cas.letra = reveladas[col]; cas.estado = EstadoCasilla.VERDE; cas._draw()
            else:
                cas.letra = "X"; cas.estado = EstadoCasilla.ACTIVO; cas._draw()

    def revelar(self, fila: int, intento: str, colores: List[EstadoCasilla], oculto=False):
        def rev(col):
            if col < len(colores):
                letra = "X" if oculto and colores[col] != EstadoCasilla.VERDE else intento[col]
                self.casillas[fila][col].set_estado(colores[col], letra)
                self.after(110, lambda: rev(col+1))
        rev(0)

    def iluminar_victoria(self, fila: int, palabra: str):
        """Ilumina toda la fila en verde (victoria)."""
        def il(col):
            if col < len(self.casillas[fila]):
                cas = self.casillas[fila][col]
                cas.letra = palabra[col] if col < len(palabra) else ""
                cas.set_estado(EstadoCasilla.VERDE, animar=True)
                self.after(80, lambda: il(col+1))
        il(0)

    def limpiar_activa(self, fila: int, reveladas: list):
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(reveladas) and reveladas[col] is not None:
                cas.letra = reveladas[col]; cas.estado = EstadoCasilla.VERDE; cas._draw()
            else:
                cas.letra = ""; cas.estado = EstadoCasilla.ACTIVO; cas._draw()

    def limpiar_activa_oculta(self, fila: int, reveladas: list):
        for col, cas in enumerate(self.casillas[fila]):
            if col < len(reveladas) and reveladas[col] is not None:
                cas.letra = reveladas[col]; cas.estado = EstadoCasilla.VERDE; cas._draw()
            else:
                cas.letra = "X"; cas.estado = EstadoCasilla.ACTIVO; cas._draw()


# ── Ahorcado ──────────────────────────────────────────────────────────────────
class Ahorcado(tk.Canvas):
    W, H = 110, 140

    def __init__(self, parent, color=C["humano"], **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=C["carta"], highlightthickness=0, **kw)
        self.errores = 0; self.color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        g = C["gris_txt"]
        # Patíbulo
        self.create_line(8, self.H-8, self.W-8, self.H-8, fill=g, width=3, capstyle=tk.ROUND)
        self.create_line(25, self.H-8, 25, 12, fill=g, width=3, capstyle=tk.ROUND)
        self.create_line(25, 12, 72, 12, fill=g, width=3, capstyle=tk.ROUND)
        self.create_line(72, 12, 72, 30, fill=g, width=2, capstyle=tk.ROUND)

        c = self.color
        if self.errores >= 1:  # cabeza
            self.create_oval(57, 30, 87, 60, outline=c, width=3)
            self.create_arc(63, 47, 81, 58, start=0, extent=-180, outline=c, width=2)
        if self.errores >= 2:  # cuerpo
            self.create_line(72, 60, 72, 98, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 3:  # brazo izq
            self.create_line(72, 70, 52, 88, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 4:  # brazo der
            self.create_line(72, 70, 92, 88, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 5:  # pierna izq
            self.create_line(72, 98, 52, 122, fill=c, width=3, capstyle=tk.ROUND)
        if self.errores >= 6:  # pierna der
            self.create_line(72, 98, 92, 122, fill=c, width=3, capstyle=tk.ROUND)
            # ojos X
            for dx, ex in [(57,63),(77,83)]:
                self.create_line(dx,36,ex,42,fill=c,width=2)
                self.create_line(ex,36,dx,42,fill=c,width=2)

    def set_errores(self, n: int):
        self.errores = min(6, n); self._draw()

    def reset(self):
        self.errores = 0; self._draw()


# ── Cronómetro ────────────────────────────────────────────────────────────────
class Cronometro(tk.Canvas):
    W, H = 220, 64

    def __init__(self, parent, total=30, on_fin=None, **kw):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=C["bg"], highlightthickness=0, **kw)
        self.total = total; self.restante = total; self.on_fin = on_fin
        self._activo = False; self._tarea = None
        self._draw()

    def _draw(self):
        self.delete("all")
        r = self.restante / self.total
        color = C["verde"] if r > 0.6 else C["dorado"] if r > 0.3 else C["rojo"]
        w, h = self.W, self.H
        bw = int((w-24) * r)
        self._rrect(12, 38, w-12, 54, 7, fill=C["oscuro"], outline="")
        if bw > 0:
            self._rrect(12, 38, 12+bw, 54, 7, fill=color, outline="")
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


# ── Menú Principal ────────────────────────────────────────────────────────────
class PantallaMenu(tk.Frame):
    def __init__(self, parent, on_iniciar: Callable, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.on_iniciar = on_iniciar
        self.cat_var  = tk.StringVar()
        self.lon_var  = tk.IntVar(value=5)
        self.modo_var = tk.StringVar(value="cat1")
        self._build()

    def _build(self):
        # Fondo punteado
        bg_c = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        bg_c.place(relx=0, rely=0, relwidth=1, relheight=1)
        for i in range(0, 1200, 45):
            for j in range(0, 900, 45):
                bg_c.create_oval(i,j,i+2,j+2, fill="#1A1A3A", outline="")

        # Contenedor central scrollable-friendly
        outer = tk.Frame(self, bg=C["bg"])
        outer.place(relx=0.5, rely=0.5, anchor="center")

        # Título
        tk.Label(outer, text="⚔", font=("Courier New", 52),
                 bg=C["bg"], fg=C["dorado"]).pack()
        tk.Label(outer, text="DUELO DE PALABRAS",
                 font=("Courier New", 30, "bold"), bg=C["bg"], fg=C["blanco"]).pack()
        tk.Label(outer, text="Humano  vs.  Inteligencia Artificial",
                 font=("Courier New", 12), bg=C["bg"], fg=C["gris_txt"]).pack(pady=(2,28))

        panel = tk.Frame(outer, bg=C["carta"], padx=35, pady=28)
        panel.pack()

        # Categoría
        self._label_sec(panel, "CATEGORÍA (visible solo para ti)")
        gestor_t = GestorJuego(DATASET_PATH)
        cats = gestor_t.get_categorias()
        self.cat_var.set(cats[0]["key"])
        f_cats = tk.Frame(panel, bg=C["carta"]); f_cats.pack(fill="x", pady=(5,18))
        self._bots_cat = {}
        for i, cat in enumerate(cats):
            b = self._chip(f_cats, f"{cat['emoji']} {cat['nombre']}",
                           lambda k=cat["key"]: self._sel_cat(k),
                           C["dorado"], C["input"])
            b.grid(row=i//3, column=i%3, padx=3, pady=3, sticky="ew")
            f_cats.columnconfigure(i%3, weight=1)
            self._bots_cat[cat["key"]] = b
        self._sel_cat(cats[0]["key"])

        # Longitud
        self._label_sec(panel, "LONGITUD DE PALABRA")
        f_lon = tk.Frame(panel, bg=C["carta"]); f_lon.pack(fill="x", pady=(5,18))
        self._bots_lon = {}
        for lon in [4, 5, 6]:
            b = self._chip(f_lon, f"{lon} letras",
                           lambda l=lon: self._sel_lon(l), C["verde"], C["input"])
            b.pack(side=tk.LEFT, padx=3, expand=True, fill="x")
            self._bots_lon[lon] = b
        self._sel_lon(5)

        # Modo IA
        self._label_sec(panel, "MODO DE LA IA")
        f_modo = tk.Frame(panel, bg=C["carta"]); f_modo.pack(fill="x", pady=(5,24))
        self._bots_modo = {}
        modos = [
            ("cat1","🔵 Modo Básico","Solo letras reveladas secuencialmente"),
            ("cat2","🟡 Modo Avanzado","Letras + pistas cromáticas (Transformer)"),
        ]
        for key, lbl, desc in modos:
            f = tk.Frame(f_modo, bg=C["input"], padx=12, pady=8, cursor="hand2")
            f.pack(side=tk.LEFT, padx=3, expand=True, fill="x")
            tk.Label(f, text=lbl, font=("Courier New",10,"bold"),
                     bg=C["input"], fg=C["blanco"]).pack(anchor="w")
            tk.Label(f, text=desc, font=("Courier New",8),
                     bg=C["input"], fg=C["gris_txt"]).pack(anchor="w")
            for w in [f]+list(f.winfo_children()):
                w.bind("<Button-1>", lambda e, k=key: self._sel_modo(k))
            self._bots_modo[key] = f
        self._sel_modo("cat1")

        # Botón iniciar
        btn = tk.Canvas(panel, width=260, height=50,
                        bg=C["carta"], highlightthickness=0, cursor="hand2")
        btn.pack()
        def _draw_btn(hover=False):
            btn.delete("all")
            col = C["verde_d"] if hover else C["verde"]
            btn.create_rectangle(0,0,260,50, fill=col, outline="")
            btn.create_text(130,25, text="⚡  INICIAR DUELO",
                            font=("Courier New",14,"bold"), fill="#000000")
        _draw_btn()
        btn.bind("<Enter>", lambda e: _draw_btn(True))
        btn.bind("<Leave>", lambda e: _draw_btn(False))
        btn.bind("<Button-1>", lambda e: self._iniciar())

    def _label_sec(self, parent, texto):
        tk.Label(parent, text=texto, font=("Courier New",9,"bold"),
                 bg=C["carta"], fg=C["gris_txt"]).pack(anchor="w")

    def _chip(self, parent, texto, cmd, col_on, col_off):
        b = tk.Label(parent, text=texto, font=("Courier New",10),
                     bg=col_off, fg=C["blanco"], padx=10, pady=7, cursor="hand2")
        b.bind("<Button-1>", lambda e: cmd())
        b._on = col_on; b._off = col_off
        return b

    def _sel_cat(self, key):
        self.cat_var.set(key)
        for k, b in self._bots_cat.items():
            b.config(bg=b._on if k==key else b._off,
                     fg="#000000" if k==key else C["blanco"])

    def _sel_lon(self, lon):
        self.lon_var.set(lon)
        for l, b in self._bots_lon.items():
            b.config(bg=b._on if l==lon else b._off,
                     fg="#000000" if l==lon else C["blanco"])

    def _sel_modo(self, key):
        self.modo_var.set(key)
        for k, f in self._bots_modo.items():
            col = C["azul"] if k==key else C["input"]
            f.config(bg=col)
            for ch in f.winfo_children(): ch.config(bg=col)

    def _iniciar(self):
        self.on_iniciar(self.cat_var.get(), self.lon_var.get(), self.modo_var.get())


# ── Pantalla de Juego ─────────────────────────────────────────────────────────
class PantallaJuego(tk.Frame):
    def __init__(self, parent, on_volver: Callable, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.on_volver = on_volver
        self.gestor: Optional[GestorJuego] = None
        self.agente: Optional[AgenteIA]   = None
        self._bloqueado    = False
        self._humano_ok    = False
        self._ia_ok        = False
        self._hilo_ia      = None
        self._texto_actual = ""
        # Guardamos intentos reales de la IA (ocultos hasta el final)
        self._intentos_ia_reales: List[str] = []
        self._juego_terminado = False
        self._build()

    # ── Construcción ──────────────────────────────────────────────────────────
    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["panel"], pady=8)
        hdr.pack(fill="x")
        hdr.columnconfigure(1, weight=1)

        btn_v = tk.Label(hdr, text="← Menú", font=("Courier New",10),
                         bg=C["panel"], fg=C["gris_txt"], cursor="hand2", padx=12)
        btn_v.pack(side=tk.LEFT)
        btn_v.bind("<Button-1>", lambda e: self._volver())

        self.lbl_turno = tk.Label(hdr, text="Turno 1 / 6",
                                   font=("Courier New",13,"bold"),
                                   bg=C["panel"], fg=C["blanco"])
        self.lbl_turno.pack(side=tk.LEFT, expand=True)

        self.lbl_cat = tk.Label(hdr, text="", font=("Courier New",10),
                                 bg=C["panel"], fg=C["dorado"], padx=12)
        self.lbl_cat.pack(side=tk.RIGHT)

        # Cronómetro
        f_crono = tk.Frame(self, bg=C["bg"]); f_crono.pack(pady=6)
        self.crono = Cronometro(f_crono, total=30, on_fin=self._tiempo_agotado)
        self.crono.pack()

        # Pista de categoría (visible para el humano)
        self.lbl_pista = tk.Label(self, text="",
                                   font=("Courier New",11,"bold"),
                                   bg=C["bg"], fg=C["dorado"])
        self.lbl_pista.pack(pady=(0,4))

        # Zona de juego: dos columnas iguales
        self.area = tk.Frame(self, bg=C["bg"])
        self.area.pack(fill="both", expand=True, padx=10, pady=4)
        self.area.columnconfigure(0, weight=1, uniform="col")
        self.area.columnconfigure(2, weight=1, uniform="col")
        self.area.columnconfigure(1, weight=0)  # separador

        self.p_humano = self._mk_panel(self.area, "👤  TÚ", C["humano"], es_humano=True)
        self.p_humano.grid(row=0, column=0, sticky="nsew", padx=(0,5))

        sep = tk.Frame(self.area, bg=C["borde"], width=2)
        sep.grid(row=0, column=1, sticky="ns", pady=20)

        self.p_ia = self._mk_panel(self.area, "🤖  IA", C["ia"], es_humano=False)
        self.p_ia.grid(row=0, column=2, sticky="nsew", padx=(5,0))

        # Input
        f_inp = tk.Frame(self, bg=C["bg"]); f_inp.pack(fill="x", padx=24, pady=6)
        inp_inner = tk.Frame(f_inp, bg=C["input"], pady=6, padx=14)
        inp_inner.pack(fill="x")
        inp_inner.columnconfigure(0, weight=1)

        self.evar = tk.StringVar()
        self.entry = tk.Entry(inp_inner, textvariable=self.evar,
                               font=("Courier New",18,"bold"),
                               bg=C["input"], fg=C["blanco"],
                               insertbackground=C["verde"], relief="flat")
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda e: self._enviar())

        self.btn_env = tk.Label(inp_inner, text="ENVIAR →",
                                 font=("Courier New",11,"bold"),
                                 bg=C["verde"], fg="#000000",
                                 padx=14, pady=6, cursor="hand2")
        self.btn_env.grid(row=0, column=1)
        self.btn_env.bind("<Button-1>", lambda e: self._enviar())

        # Estado
        self.lbl_estado = tk.Label(self, text="",
                                    font=("Courier New",10),
                                    bg=C["bg"], fg=C["gris_txt"])
        self.lbl_estado.pack(pady=2)

    def _mk_panel(self, parent, titulo, color, es_humano) -> tk.Frame:
        panel = tk.Frame(parent, bg=C["carta"], padx=12, pady=12)

        tk.Label(panel, text=titulo, font=("Courier New",13,"bold"),
                 bg=C["carta"], fg=color).pack(pady=(0,6))

        ahorcado = Ahorcado(panel, color=color)
        ahorcado.pack()

        if not es_humano:
            # Botón historial IA (inactivo durante el juego)
            btn_h = tk.Label(panel, text="🔍 Ver historial IA",
                              font=("Courier New",8),
                              bg=C["input"], fg=C["gris_txt"],
                              padx=8, pady=4, cursor="hand2")
            btn_h.pack(pady=(4,2))
            btn_h.bind("<Button-1>", lambda e: self._ver_historial_ia())
            panel._btn_hist = btn_h

        tablero = Tablero(panel, filas=6, cols=5)
        tablero.pack(pady=6)

        lbl_env = tk.Label(panel, text="", font=("Courier New",9),
                            bg=C["carta"], fg=C["verde"])
        lbl_env.pack()

        panel._ahorcado = ahorcado
        panel._tablero  = tablero
        panel._lbl_env  = lbl_env
        panel._color    = color
        panel._es_humano = es_humano
        return panel

    # ── Iniciar partida ───────────────────────────────────────────────────────
    def iniciar(self, categoria: str, longitud: int, modo: str):
        self.gestor = GestorJuego(DATASET_PATH)
        self.agente = AgenteIA(DATASET_PATH, modo=modo)
        self._intentos_ia_reales = []
        self._juego_terminado = False

        palabra = self.gestor.iniciar_partida(categoria, longitud)
        print(f"[DEBUG] Palabra secreta: {palabra}")

        # Reconfigurar tableros
        self.p_humano._tablero.reconfigurar(longitud)
        self.p_ia._tablero.reconfigurar(longitud)

        # Reset ahorcados
        self.p_humano._ahorcado.reset()
        self.p_ia._ahorcado.reset()

        # Info categoría
        cats = self.gestor.get_categorias()
        cat_info = next((c for c in cats if c["key"]==categoria), None)
        if cat_info:
            self.lbl_pista.config(text=f"🎯  Categoría: {cat_info['emoji']} {cat_info['nombre']}")
            self.lbl_cat.config(text=f"{cat_info['emoji']} {cat_info['nombre']}")

        self._prep_turno()
        self.crono.iniciar()
        self._lanzar_ia()

    def _prep_turno(self):
        t = self.gestor.turno_actual
        self.lbl_turno.config(text=f"Turno {t+1} / 6")
        self._bloqueado  = False
        self._humano_ok  = False
        self._ia_ok      = False
        self._texto_actual = ""
        self.evar.set("")
        self.entry.config(state="normal")
        self.btn_env.config(bg=C["verde"])
        self.entry.focus()
        self.p_humano._lbl_env.config(text="")
        self.p_ia._lbl_env.config(text="🤖 Pensando...")
        self.lbl_estado.config(
            text="⏱  Escribe tu palabra y presiona ENVIAR", fg=C["gris_txt"])

        # Mostrar letras reveladas en la fila activa
        rev = self.gestor.letras_reveladas
        self.p_humano._tablero.limpiar_activa(t, rev)
        self.p_ia._tablero.limpiar_activa_oculta(t, rev)

    # ── Interacción humano ────────────────────────────────────────────────────
    def _on_key(self, event):
        if self._bloqueado: return
        texto = ''.join(c for c in self.evar.get().upper() if c.isalpha())
        lon = self.gestor.longitud_palabra
        texto = texto[:lon]
        self.evar.set(texto)
        self._texto_actual = texto
        t = self.gestor.turno_actual
        self.p_humano._tablero.mostrar_intento(t, texto, self.gestor.letras_reveladas)

    def _enviar(self):
        if self._bloqueado or self._humano_ok: return
        intento = self.evar.get().upper()
        lon = self.gestor.longitud_palabra
        if len(intento) != lon:
            self.lbl_estado.config(
                text=f"⚠  La palabra debe tener {lon} letras", fg=C["rojo"])
            return
        resultado = self.gestor.registrar_intento_humano(intento)
        if resultado is None: return
        self._humano_ok = True
        self.entry.config(state="disabled")
        self.btn_env.config(bg=C["gris"])
        self.p_humano._lbl_env.config(text="✅ Enviado")
        if self._ia_ok:
            self._cerrar_turno()
        else:
            self.lbl_estado.config(text="⏳ Esperando a la IA…", fg=C["gris_txt"])

    # ── IA ────────────────────────────────────────────────────────────────────
    def _lanzar_ia(self):
        if self.gestor and self.agente:
            self._hilo_ia = self.agente.pensar_async(
                self.gestor, self._cb_ia)

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

    # ── Tiempo agotado ────────────────────────────────────────────────────────
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
            self.lbl_estado.config(text="⏳ Esperando a la IA…", fg=C["dorado"])
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

    # ── Cierre de turno ───────────────────────────────────────────────────────
    def _cerrar_turno(self):
        if self._bloqueado: return
        self._bloqueado = True
        self.crono.detener()
        t = self.gestor.turno_actual

        # Revelar humano
        if self.gestor.humano.feedbacks:
            fb_h = self.gestor.humano.feedbacks[-1]
            int_h = self.gestor.humano.intentos[-1]
            self.p_humano._tablero.revelar(t, int_h, fb_h, oculto=False)

        # Revelar IA (oculto = X salvo verdes)
        if self.gestor.ia.feedbacks:
            fb_ia = self.gestor.ia.feedbacks[-1]
            int_ia = self.gestor.ia.intentos[-1]
            self.p_ia._tablero.revelar(t, int_ia, fb_ia, oculto=True)

        # Avanzar turno en la lógica
        self.gestor.avanzar_turno()

        # Actualizar ahorcados DESPUÉS de avanzar (errores ya actualizados)
        self.p_humano._ahorcado.set_errores(self.gestor.humano.errores)
        self.p_ia._ahorcado.set_errores(self.gestor.ia.errores)

        delay = 1600
        if self.gestor.is_game_over():
            # Si alguien ganó, iluminar su fila en verde
            ganador = self.gestor.get_ganador()
            palabra = self.gestor.palabra_secreta
            if ganador in ("humano", "empate") and self.gestor.humano.gano:
                self.after(400, lambda: self.p_humano._tablero.iluminar_victoria(t, palabra))
            if ganador in ("ia", "empate") and self.gestor.ia.gano:
                self.after(400, lambda: self.p_ia._tablero.iluminar_victoria(t, palabra))
            self.after(delay + 600, self._resultado_final)
        else:
            self.after(delay, self._sig_turno)

    def _sig_turno(self):
        self._prep_turno()
        self.crono.iniciar()
        self._lanzar_ia()

    # ── Resultado final ───────────────────────────────────────────────────────
    def _resultado_final(self):
        self._juego_terminado = True
        ganador = self.gestor.get_ganador()
        palabra = self.gestor.palabra_secreta

        ven = tk.Toplevel(self)
        ven.title("Resultado Final")
        ven.configure(bg=C["bg"])
        ven.geometry("520x440")
        ven.resizable(False, False)
        ven.grab_set()
        ven.focus_force()

        f = tk.Frame(ven, bg=C["bg"]); f.pack(fill="both", expand=True, padx=28, pady=24)

        if ganador == "humano":
            emo, tit, col = "🏆", "¡GANASTE!", C["dorado"]
        elif ganador == "ia":
            emo, tit, col = "🤖", "LA IA GANÓ", C["azul"]
        elif ganador == "empate":
            emo, tit, col = "🤝", "¡EMPATE!", C["verde"]
        else:
            emo, tit, col = "💀", "NADIE GANÓ", C["rojo"]

        tk.Label(f, text=emo, font=("Courier New",52),
                 bg=C["bg"], fg=col).pack()
        tk.Label(f, text=tit, font=("Courier New",26,"bold"),
                 bg=C["bg"], fg=col).pack(pady=4)
        tk.Label(f, text=f"La palabra era:  {palabra}",
                 font=("Courier New",15), bg=C["bg"], fg=C["blanco"]).pack(pady=8)

        stats = tk.Frame(f, bg=C["carta"], padx=18, pady=12)
        stats.pack(fill="x", pady=8)
        h_n = len(self.gestor.humano.intentos)
        ia_n = len(self.gestor.ia.intentos)
        tk.Label(stats,
                 text=f"👤 Tú: {'✅ Acertó' if self.gestor.humano.gano else '❌ Falló'} ({h_n} {'intento' if h_n==1 else 'intentos'})",
                 font=("Courier New",11), bg=C["carta"], fg=C["humano"]).pack(anchor="w")
        tk.Label(stats,
                 text=f"🤖 IA: {'✅ Acertó' if self.gestor.ia.gano else '❌ Falló'} ({ia_n} {'intento' if ia_n==1 else 'intentos'})",
                 font=("Courier New",11), bg=C["carta"], fg=C["ia"]).pack(anchor="w")

        # Botones
        bf = tk.Frame(f, bg=C["bg"]); bf.pack(pady=12)

        b_hist = tk.Label(bf, text="🔍 Ver historial IA",
                           font=("Courier New",11), bg=C["input"],
                           fg=C["blanco"], padx=14, pady=8, cursor="hand2")
        b_hist.pack(side=tk.LEFT, padx=4)
        b_hist.bind("<Button-1>", lambda e: self._ver_historial_ia_full())

        b_nuevo = tk.Label(bf, text="▶ Nueva partida",
                            font=("Courier New",11,"bold"), bg=C["verde"],
                            fg="#000000", padx=14, pady=8, cursor="hand2")
        b_nuevo.pack(side=tk.LEFT, padx=4)
        b_nuevo.bind("<Button-1>", lambda e: [ven.destroy(), self._volver()])

        b_menu = tk.Label(bf, text="⇐ Menú",
                           font=("Courier New",11), bg=C["oscuro"],
                           fg=C["blanco"], padx=14, pady=8, cursor="hand2")
        b_menu.pack(side=tk.LEFT, padx=4)
        b_menu.bind("<Button-1>", lambda e: [ven.destroy(), self._volver()])

    # ── Historial IA ──────────────────────────────────────────────────────────
    def _ver_historial_ia(self):
        if not self._juego_terminado:
            messagebox.showinfo("Historial IA",
                                "El historial de la IA se revela\nal terminar la partida.")
            return
        self._ver_historial_ia_full()

    def _ver_historial_ia_full(self):
        ven = tk.Toplevel(self)
        ven.title("🤖 Predicciones de la IA")
        ven.configure(bg=C["bg"])
        ven.geometry("620x520")
        ven.focus_force()

        tk.Label(ven, text="🧠 Historial de Predicciones de la IA",
                 font=("Courier New",13,"bold"),
                 bg=C["bg"], fg=C["azul"]).pack(pady=12)

        canvas = tk.Canvas(ven, bg=C["bg"], highlightthickness=0)
        sb = tk.Scrollbar(ven, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        fs = tk.Frame(canvas, bg=C["bg"])
        canvas.create_window((0,0), window=fs, anchor="nw")

        for h in self.gestor.historial_ia:
            card = tk.Frame(fs, bg=C["carta"], padx=14, pady=10)
            card.pack(fill="x", padx=12, pady=4)
            tk.Label(card, text=f"Turno {h.turno+1}",
                     font=("Courier New",12,"bold"), bg=C["carta"],
                     fg=C["azul"]).pack(anchor="w")
            tk.Label(card,
                     text=f"Patrón: {h.patron}  |  Pistas grises: {h.letras_pista}  |  {h.tiempo_ms:.1f}ms",
                     font=("Courier New",8), bg=C["carta"], fg=C["gris_txt"]).pack(anchor="w")
            tk.Label(card, text=f"✅ Seleccionó: {h.seleccionada}",
                     font=("Courier New",11,"bold"), bg=C["carta"],
                     fg=C["verde"]).pack(anchor="w", pady=(3,0))
            if h.candidatos:
                tops = "  ".join(f"{p}({prob:.2f})" for p,prob in h.candidatos[:3])
                tk.Label(card, text=f"Top: {tops}", font=("Courier New",8),
                         bg=C["carta"], fg=C["gris"]).pack(anchor="w")

        fs.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _volver(self):
        self.crono.detener()
        self.on_volver()


# ── App ───────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Duelo de Palabras ⚔")
        self.configure(bg=C["bg"])
        self.minsize(860, 680)

        # Responsivo: empezar con un tamaño razonable
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(1100, sw - 80)
        h  = min(800,  sh - 80)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
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
