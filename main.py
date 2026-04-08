import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
from tkcalendar import DateEntry
from utils.interface import *
from statistics.graphs import Graphs

try:
    from clients.osrm_client import OsrmClient
    from clients.train_client import TrainClient
    from clients.amadeus_client import AmadeusClient
    from services.flight_service import FlightService
    from services.car_service import CarService
    from services.train_service import TrainService
    from services.hotel_service import HotelService
    BACKEND_AVAILABLE = True
except Exception as e:
    BACKEND_AVAILABLE = False
    BACKEND_ERROR = str(e)

# ─── Autocomplete Entry ───────────────────────────────────────────────────────

class AutocompleteEntry(tk.Frame):
    def __init__(self, parent, suggestions, textvariable=None, width=18, **kw):
        super().__init__(parent, bg=C["input_bd"], padx=1, pady=1)
        self.suggestions = suggestions
        self.var = textvariable or tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, width=width, font=FB, fg=C["text"], bg=C["input"],
                              insertbackground=C["accent1"], relief="flat", bd=4, highlightthickness=0)
        self.entry.pack(fill="x")
        self._win = None
        self._lb = None
        self.var.trace_add("write", self._on_type)
        self.entry.bind("<FocusOut>", lambda e: self.after(150, self._hide))
        self.entry.bind("<Escape>", lambda e: self._hide())
        self.entry.bind("<Return>", lambda e: self._hide())
        self.entry.bind("<Down>", self._focus_list)

    def get(self):
        return self.var.get()

    def _on_type(self, *_):
        typed = self.var.get().strip().lower()
        if not typed:
            self._hide()
            return
        matches = [s for s in self.suggestions if s.lower().startswith(typed)][:8]
        if matches:
            self._show(matches)
        else:
            self._hide()

    def _show(self, matches):
        if self._win:
            self._win.destroy()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        w = self.entry.winfo_width()
        h = min(len(matches) * 22 + 4, 180)
        self._win = tk.Toplevel(self)
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(f"{w}x{h}+{x}+{y}")
        self._win.lift()
        self._lb = tk.Listbox(self._win, font=FB, fg=C["text"], bg=C["panel"], selectbackground=C["accent1"],
                              selectforeground="white", relief="flat", bd=0, activestyle="none", highlightthickness=1,
                              highlightbackground=C["input_bd"])
        self._lb.pack(fill="both", expand=True)
        for m in matches:
            self._lb.insert("end", m)
        self._lb.bind("<ButtonRelease-1>", self._pick)
        self._lb.bind("<Return>", self._pick)

    def _pick(self, _=None):
        if self._lb:
            sel = self._lb.curselection()
            if sel:
                self.var.set(self._lb.get(sel[0]))
        self._hide()

    def _focus_list(self, _=None):
        if self._lb:
            self._lb.focus_set()
            self._lb.selection_set(0)

    def _hide(self):
        if self._win:
            self._win.destroy()
            self._win = self._lb = None

# ─── Dual Range Slider (single compact container) ────────────────────────────

class DualRangeSlider(tk.Frame):
    """Min and max price sliders in one visually unified box."""
    def __init__(self, parent, min_val=0, max_val=2000):
        super().__init__(parent, bg=C["panel"], highlightthickness=1, highlightbackground=C["input_bd"], padx=10, pady=8)
        self.var_min = tk.IntVar(value=min_val)
        self.var_max = tk.IntVar(value=max_val)

        # ── Header row showing both values ──────────────────────────────────
        header = tk.Frame(self, bg=C["panel"])
        header.pack(fill="x", pady=(0, 6))
        lbl(header, "Price range", font=FSB, bg=C["panel"],
            fg=C["text"]).pack(side="left")
        self.lbl_range = lbl(header,f"€{min_val} – €{max_val}", font=FSB, bg=C["panel"], fg=C["accent1"])
        self.lbl_range.pack(side="right")

        sk = dict(orient="horizontal", from_=0, to=max_val, bg=C["panel"], fg=C["text"], troughcolor=C["border"],
                  highlightthickness=0, activebackground=C["accent1"], font=FS, length=210, showvalue=False)

        # ── Min slider ──────────────────────────────────────────────────────
        min_row = tk.Frame(self, bg=C["panel"])
        min_row.pack(fill="x")
        lbl(min_row, "Min", font=FS, fg=C["subtext"], bg=C["panel"], width=3, anchor="w").pack(side="left")
        tk.Scale(self, variable=self.var_min, command=self._on_change, **sk).pack(fill="x")

        # ── Max slider ──────────────────────────────────────────────────────
        max_row = tk.Frame(self, bg=C["panel"])
        max_row.pack(fill="x")
        lbl(max_row, "Max", font=FS, fg=C["subtext"], bg=C["panel"], width=3, anchor="w").pack(side="left")
        s2 = tk.Scale(self, variable=self.var_max, command=self._on_change, **sk)
        s2.set(max_val)
        s2.pack(fill="x")

    def _on_change(self, _=None):
        lo, hi = self.var_min.get(), self.var_max.get()
        if lo > hi:
            self.var_min.set(hi)
            lo = hi
        self.lbl_range.config(text=f"€{lo} – €{hi}")

    def get(self):
        lo, hi = self.var_min.get(), self.var_max.get()
        return min(lo, hi), max(lo, hi)

# ─── Sort Button Bar ─────────────────────────────────────────────────────────

class SortBar(tk.Frame):
    """Pill-style toggle buttons for sort order."""

    OPTS = [ ("💰  Price", "price"), ("⏱  Duration", "duration"),
        ("🎯  Comfort", "comfort"), ("⭐  Best overall", "overall"), ]

    def __init__(self, parent, on_change, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self._on_change = on_change
        self._btns = {}
        self._var = tk.StringVar(value="price")

        for label, val in self.OPTS:
            b = tk.Button( self, text=label, font=FS, relief="flat", bd=0, padx=10, pady=5,
                cursor="hand2", command=lambda v=val: self._select(v) )
            b.pack(side="left", padx=2)
            self._btns[val] = b

        self._select("price", notify=False)

    def _select(self, val, notify=True):
        self._var.set(val)
        for v, b in self._btns.items():
            if v == val:
                b.config(bg=C["accent1"], fg="white", activebackground=C["accent1"], activeforeground="white")
            else:
                b.config(bg=C["border"], fg=C["text"], activebackground=C["input_bd"], activeforeground=C["text"])
        if notify:
            self._on_change()

    def get(self):
        return self._var.get()


# ─── Main App ─────────────────────────────────────────────────────────────────

class TravelApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.graphs = Graphs()
        self.title("✈ Travel Offer Manager")
        self.configure(bg=C["bg"])
        self.geometry("1180x790")
        self.minsize(960, 660)
        self.resizable(True, True)
        self._init_services()
        self.results = []
        self.hotel_results = []
        self._build_header()
        self._build_tabs()


    def _init_services(self):
        self.flight_svc = self.car_svc = self.train_svc = self.hotel_svc = None
        if not BACKEND_AVAILABLE:
            return
        try:
            client = AmadeusClient()
            self.flight_svc = FlightService(client)
            self.hotel_svc = HotelService(client)
        except Exception:
            pass
        try:
            self.car_svc = CarService()
            self.train_svc = TrainService()
        except Exception:
            pass

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        h = tk.Frame(self, bg=C["hdr_bg"], pady=11)
        h.pack(fill="x")
        lbl(h, "  ✈  TRAVEL OFFER MANAGER", font=FT, fg=C["hdr_fg"], bg=C["hdr_bg"]).pack(side="left", padx=20)
        status = "● Backend connected" if BACKEND_AVAILABLE else "● Demo mode"
        scol = C["ok"] if BACKEND_AVAILABLE else C["warn"]
        lbl(h, status + "  ", font=FS, fg=scol, bg=C["hdr_bg"]).pack(side="right", padx=16)

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _build_tabs(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TNotebook", background=C["bg"], borderwidth=0, tabmargins=0)
        style.configure("App.TNotebook.Tab", background=C["border"], foreground=C["subtext"], font=FH, padding=[20, 8], borderwidth=0)
        style.map("App.TNotebook.Tab", background=[("selected", C["panel"])], foreground=[("selected", C["accent1"])])

        nb = ttk.Notebook(self, style="App.TNotebook")
        nb.pack(fill="both", expand=True)

        t1 = tk.Frame(nb, bg=C["bg"])
        nb.add(t1, text="  🔍  Search Travels  ")
        self._build_travel_tab(t1)

        t2 = tk.Frame(nb, bg=C["bg"])
        nb.add(t2, text="  🏨  Hotels  ")
        self._build_hotel_tab(t2)

        t3 = tk.Frame(nb, bg=C["bg"])
        nb.add(t3, text="  📊  Statistics  ")
        self.graphs._build_stats_tab(t3)

    # =========================================================================
    #  TAB 1 – SEARCH
    # =========================================================================

    def _build_travel_tab(self, parent):
        sidebar = tk.Frame(parent, bg=C["panel"], width=330)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        vsep(parent).pack(side="left", fill="y")
        right = tk.Frame(parent, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        self._build_search_panel(sidebar)
        self._build_results_panel(right)

    def _build_search_panel(self, parent):
        lbl(parent, "  Search", font=FH, fg=C["accent1"], bg=C["panel"]).pack(anchor="w", pady=(14, 2), padx=10)
        hsep(parent)

        # ── Container + Scroll ─────────────────────────
        container = tk.Frame(parent, bg=C["panel"])
        container.pack(fill="both", expand=True)

        sc = tk.Canvas(container, bg=C["panel"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=sc.yview)
        sc.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        sc.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(sc, bg=C["panel"])
        win = sc.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: sc.configure(scrollregion=sc.bbox("all")))
        sc.bind("<Configure>",
                lambda e: sc.itemconfig(win, width=e.width))

        def _on_mousewheel(event):
            sc.yview_scroll(int(-1 * (event.delta / 120)), "units")

        sc.bind_all("<MouseWheel>", _on_mousewheel)

        # ── FORM – common fields ───────────────────────
        f = tk.Frame(inner, bg=C["panel"], padx=14)
        f.pack(fill="x", pady=4)
        f.columnconfigure(1, weight=1)

        lbl(f, "From", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_origin = AutocompleteEntry(f, CITY_SUGGESTIONS, width=17)
        self.entry_origin.grid(row=0, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "To", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_dest = AutocompleteEntry(f, CITY_SUGGESTIONS, width=17)
        self.entry_dest.grid(row=1, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Departure", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=2, column=0, sticky="w", pady=5)
        self.var_depart = tk.StringVar()
        dw, _ = outlined_date(f, self.var_depart, width=14)
        dw.grid(row=2, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Return", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=3, column=0, sticky="w", pady=5)
        self.var_return = tk.StringVar()
        rw, _ = outlined_date(f, self.var_return, width=14)
        rw.grid(row=3, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Adults", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=4, column=0, sticky="w", pady=5)
        self.var_adults = tk.StringVar(value="1")
        styled_combo(f, ["1", "2", "3", "4", "5", "6"], self.var_adults, width=5) \
            .grid(row=4, column=1, sticky="w", pady=5, padx=(6, 0))

        lbl(f, "Currency", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=5, column=0, sticky="w", pady=5)
        self.var_currency = tk.StringVar(value="EUR")
        styled_combo(f, ["EUR", "RON", "USD", "GBP"], self.var_currency, width=6) \
            .grid(row=5, column=1, sticky="w", pady=5, padx=(6, 0))

        hsep(inner)

        # ── Transport modes ────────────────────────────
        f4 = tk.Frame(inner, bg=C["panel"], padx=14)
        f4.pack(fill="x", pady=2)
        lbl(f4, "Transport modes", font=FSB, bg=C["panel"]).pack(anchor="w", pady=(4, 2))

        self.var_flight = tk.BooleanVar(value=True)
        self.var_car = tk.BooleanVar(value=True)
        self.var_train = tk.BooleanVar(value=True)

        def styled_check(parent, text, var):
            chk = tk.Checkbutton( parent, text=text, variable=var, font=FH, fg=C["text"],
                bg=C["panel"], activeforeground=C["text"], activebackground=C["panel"], selectcolor=C["panel"],
                highlightthickness=0, bd=0, padx=10, pady=6, cursor="hand2"  )

            def on_enter(e):
                chk.config(bg=C["hover"])

            def on_leave(e):
                chk.config(bg=C["panel"])

            chk.bind("<Enter>", on_enter)
            chk.bind("<Leave>", on_leave)

            return chk

        # ── ✈ Flight + inline options ─────────────────
        styled_check(f4, "✈  Plane", self.var_flight).pack(anchor="w", pady=2)

        self.flight_options = tk.Frame(f4, bg=C["card_alt"], padx=12, pady=6, highlightthickness=1, highlightbackground=C["input_bd"])
        fg_inner = tk.Frame(self.flight_options, bg=C["card_alt"])
        fg_inner.pack(fill="x")
        fg_inner.columnconfigure(1, weight=1)

        lbl(fg_inner, "Class", font=FS, bg=C["card_alt"], fg=C["subtext"]).grid( row=0, column=0, sticky="w", pady=3)
        self.var_travel_class = tk.StringVar(value="ECONOMY")
        styled_combo(fg_inner, ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"], self.var_travel_class, width=14).grid(
            row=0, column=1, sticky="ew", pady=3, padx=(6, 0))

        lbl(fg_inner, "Nonstop", font=FS, bg=C["card_alt"], fg=C["subtext"]).grid( row=1, column=0, sticky="w", pady=3)
        self.var_nonstop = tk.StringVar(value="false")
        nonstop_row = tk.Frame(fg_inner, bg=C["card_alt"])
        nonstop_row.grid(row=1, column=1, sticky="w", padx=(6, 0))
        for txt, val in [("Any", "false"), ("Only", "true")]:
            tk.Radiobutton(nonstop_row, text=txt, variable=self.var_nonstop, value=val, font=FS, fg=C["text"], bg=C["card_alt"],
                           selectcolor=C["accent1"], activebackground=C["card_alt"]).pack(side="left", padx=(0, 8))

        def toggle_flight_opts(*_):
            if self.var_flight.get():
                self.flight_options.pack(anchor="w", fill="x", pady=(2, 4), padx=(20, 0))
            else:
                self.flight_options.pack_forget()

        self.var_flight.trace_add("write", toggle_flight_opts)
        toggle_flight_opts()

        # ── 🚗 Car + inline options ───────────────────
        self.chk_car = styled_check(f4, "🚗  Car", self.var_car)
        self.chk_car.pack(anchor="w", pady=2)

        self.fuel_container = tk.Frame(f4, bg=C["card_alt"], padx=12, pady=6, highlightthickness=1, highlightbackground=C["input_bd"])
        fc_inner = tk.Frame(self.fuel_container, bg=C["card_alt"])
        fc_inner.pack(fill="x")
        fc_inner.columnconfigure(1, weight=1)

        lbl(fc_inner, "Fuel type", font=FSB, bg=C["card_alt"], fg=C["subtext"]).grid( row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.var_fuel = tk.StringVar(value="diesel")
        fuel_row = tk.Frame(fc_inner, bg=C["card_alt"])
        fuel_row.grid(row=1, column=0, columnspan=2, sticky="w")
        for fuel in ["gasoline", "diesel", "LPG"]:
            tk.Radiobutton(fuel_row, text=fuel, variable=self.var_fuel, value=fuel, font=FS, fg=C["text"], bg=C["card_alt"],
                           selectcolor=C["accent2"], activebackground=C["card_alt"], activeforeground=C["accent2"]).pack(side="left", padx=(0, 8))

        lbl(fc_inner, "Consumption", font=FS, bg=C["card_alt"], fg=C["subtext"]).grid( row=2, column=0, sticky="w", pady=(6, 2))
        self.var_consumption = tk.StringVar(value="")
        cons_wrap = tk.Frame(fc_inner, bg=C["input_bd"], padx=1, pady=1)
        cons_wrap.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(6, 2))
        tk.Entry(cons_wrap, textvariable=self.var_consumption, width=6, font=FB, fg=C["text"], bg=C["input"], insertbackground=C["accent1"], relief="flat", bd=3, highlightthickness=0).pack(fill="x")
        lbl(fc_inner, "  L/100km (optional)", font=FS, bg=C["card_alt"], fg=C["subtext"]).grid( row=3, column=0, columnspan=2, sticky="w")

        def toggle_fuel(*_):
            if self.var_car.get():
                self.fuel_container.pack(anchor="w", fill="x",
                                         pady=(2, 4), padx=(20, 0))
            else:
                self.fuel_container.pack_forget()

        self.var_car.trace_add("write", toggle_fuel)
        toggle_fuel()

        # ── 🚆 Train ──────────────────────────────────
        styled_check(f4, "🚆  Train", self.var_train).pack(anchor="w", pady=2)

        hsep(inner)

        # ── Price range (unified container) ──────────
        f3 = tk.Frame(inner, bg=C["panel"], padx=14)
        f3.pack(fill="x", pady=2)
        self.price_range = DualRangeSlider(f3)
        self.price_range.pack(fill="x")

        hsep(inner)

        action_btn(inner, "  🔍  Find Best Offers", self._run_search,
                   color=C["accent1"], width=30).pack(pady=12, padx=14)

        self.search_status = lbl(inner, "", font=FS, fg=C["subtext"], bg=C["panel"])
        self.search_status.pack(pady=(0, 10))

    def _build_results_panel(self, parent):
        top = tk.Frame(parent, bg=C["bg"])
        top.pack(fill="x", padx=14, pady=(10, 4))
        lbl(top, "Results", font=FH, fg=C["accent1"], bg=C["bg"]).pack(side="left")

        # ── Sort bar (pill buttons) ───────────────────────────────────────────
        sort_wrap = tk.Frame(top, bg=C["bg"])
        sort_wrap.pack(side="right")
        lbl(sort_wrap, "Sort:", font=FS, fg=C["subtext"], bg=C["bg"]).pack(side="left", padx=(0, 6))
        self.sort_bar = SortBar(sort_wrap, on_change=self._render_results)
        self.sort_bar.pack(side="left")

        hsep(parent, padx=14, pady=0)

        container = tk.Frame(parent, bg=C["bg"])
        container.pack(fill="both", expand=True, padx=14, pady=6)

        canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.results_frame = tk.Frame(canvas, bg=C["bg"])
        self._rwin = canvas.create_window((0, 0), window=self.results_frame, anchor="nw")
        self.results_frame.bind("<Configure>",
                                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self._rwin, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._show_placeholder("Enter origin and destination, then click Find Best Offers.")

    def _show_placeholder(self, msg):
        for w in self.results_frame.winfo_children():
            w.destroy()
        lbl(self.results_frame, msg, font=FB, fg=C["subtext"], bg=C["bg"]).pack(pady=50)

    def _overall_score(self, r):
        prices = [x["price"] for x in self.results] or [1]
        durations = [x["duration_min"] for x in self.results] or [1]
        rng_p = max(prices) - min(prices) or 1
        rng_d = max(durations) - min(durations) or 1
        p_n = (r["price"] - min(prices)) / rng_p
        d_n = (r["duration_min"] - min(durations)) / rng_d
        c_n = 1 - (r.get("comfort", 5) - 1) / 9
        return p_n * 0.4 + d_n * 0.35 + c_n * 0.25

    def _render_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        if not self.results:
            self._show_placeholder("No offers found for the selected criteria.")
            return
        key_map = {
            "price": lambda r: r["price"],
            "duration": lambda r: r["duration_min"],
            "comfort": lambda r: -r.get("comfort", 5),
            "overall": self._overall_score,
        }
        sorted_res = sorted(self.results,
                            key=key_map.get(self.sort_bar.get(), key_map["price"]))
        best_price = min(r["price"] for r in sorted_res)
        for i, offer in enumerate(sorted_res):
            self._render_card(offer, i, offer["price"] == best_price)

    def _render_card(self, offer, idx, is_best):
        mode = offer["mode"]
        color = MODE_COLOR.get(mode, C["accent1"])
        icon = MODE_ICON.get(mode, "?")
        bg = C["card"] if idx % 2 == 0 else C["card_alt"]
        cur = offer.get("currency", "EUR")

        card = tk.Frame(self.results_frame, bg=bg, pady=10, highlightthickness=1, highlightbackground=C["accent4"] if is_best else C["border"])
        card.pack(fill="x", pady=4)

        tk.Frame(card, bg=color, width=5).pack(side="left", fill="y")
        inner = tk.Frame(card, bg=bg, padx=12)
        inner.pack(side="left", fill="both", expand=True)

        # ── Top row: mode label + best badge + price ──
        top = tk.Frame(inner, bg=bg)
        top.pack(fill="x")
        lbl(top, f"{icon}  {mode.upper()}", font=FH, fg=color, bg=bg).pack(side="left")
        if is_best:
            lbl(top, "  ★ Best Price", font=FSB, fg=C["accent4"], bg=bg).pack(side="left", padx=6)
        lbl(top, f"{cur} {offer['price']:.2f}", font=("Segoe UI", 12, "bold"), fg=C["text"], bg=bg).pack(side="right")

        # ── Detail row 1: time / distance / speed ─────
        det1 = tk.Frame(inner, bg=bg)
        det1.pack(fill="x", pady=(3, 0))
        row1 = [ f"⏱ {fmt_time(offer['duration_min'])}", f"📍 {offer['distance_km']:.0f} km" if offer.get("distance_km") else "",
            f"⚡ {offer['speed_kmh']:.0f} km/h" if offer.get("speed_kmh") else "", f"🎯 Comfort {offer['comfort']}/10" if offer.get("comfort") else "", ]
        for t in row1:
            if t.strip():
                lbl(det1, t, font=FS, fg=C["subtext"], bg=bg).pack(side="left", padx=(0, 10))

        # ── Detail row 2: mode-specific extras ────────
        det2 = tk.Frame(inner, bg=bg)
        det2.pack(fill="x", pady=(1, 0))
        row2 = []

        if mode == "flight":
            t_class = offer.get("travel_class", "ECONOMY")
            row2.append(f"💺 {t_class.replace('_', ' ').title()}")
            if offer.get("nonstop"):
                row2.append("🚫 Nonstop")
            row2.append(offer.get("operator", ""))

        elif mode == "car":
            row2.append(offer.get("operator", ""))

        elif mode == "train":
            row2.append(offer.get("operator", ""))

        for t in row2:
            if t.strip():
                lbl(det2, t, font=FS, fg=C["subtext"], bg=bg).pack(side="left", padx=(0, 10))

    # ── Search logic ──────────────────────────────────────────────────────────

    def _run_search(self):
        origin = self.entry_origin.get().strip()
        dest = self.entry_dest.get().strip()
        if not origin or not dest:
            messagebox.showwarning("Missing input", "Please enter both origin and destination.")
            return
        if origin.lower() == dest.lower():
            messagebox.showwarning("Same city", "Origin and destination must be different.")
            return
        self.results = []
        self.graphs.results = []
        self._show_placeholder("🔄  Searching — please wait…")
        self.search_status.config(text="Fetching offers…", fg=C["accent1"])
        Thread(target=self._fetch_all, args=(origin, dest), daemon=True).start()

    def _fetch_all(self, origin, dest):
        results = []
        depart = self.var_depart.get()
        ret = self.var_return.get() or None
        adults = int(self.var_adults.get() or 1)
        fuel = self.var_fuel.get()
        currency = self.var_currency.get()
        nonstop = self.var_nonstop.get()
        t_class = self.var_travel_class.get()
        cons_raw = self.var_consumption.get().strip()
        consumption = float(cons_raw) if cons_raw else None
        p_min, p_max = self.price_range.get()

        # ── Flight ────────────────────────────────────
        if self.var_flight.get() and self.flight_svc:
            try:
                info = self.flight_svc.get_flight_info( original_city=origin, destination_city=dest,
                    departure_date=depart, return_date=ret, adult_number=adults, currency_code=currency,
                    nonstop=nonstop, travel_class=None if t_class == "ECONOMY" else t_class )
                if info:
                    results.append({ "mode": "flight", "price": info["price"][0],
                        "duration_min": info["time"][0], "comfort": 6,
                        "travel_class": t_class, "nonstop": nonstop == "true",
                        "currency": currency, "operator": "Cheapest option" })
                    if info["price"][1] != info["price"][0]:
                        results.append({ "mode": "flight", "price": info["price"][1],
                            "duration_min": info["time"][1], "comfort": 7,
                            "travel_class": t_class, "nonstop": nonstop == "true",
                            "currency": currency, "operator": "Fastest option" })
            except Exception as e:
                print(f"[Flight] {e}")

        # ── Car ───────────────────────────────────────
        if self.var_car.get() and self.car_svc:
            try:
                info = self.car_svc.get_car_info( start=origin, end=dest, car_type=None, consumption=consumption, currency_code=currency )
                if info:
                    base_price = round(info["price"] * adults, 2)
                    results.append({ "mode": "car", "price": base_price, "duration_min": int(info["time"] * 60), "distance_km": info["distance"],
                        "speed_kmh": info.get("speed"), "comfort": 7, "currency": currency,
                        "operator": f"{fuel.capitalize()} · {info['distance']:.0f} km · {adults} adult{'s' if adults > 1 else ''}" })
            except Exception as e:
                print(f"[Car] {e}")

        # ── Train ─────────────────────────────────────
        if self.var_train.get() and self.train_svc:
            try:
                info = self.train_svc.get_train_info( start=origin, end=dest, currency_code=currency )
                if info:
                    prices = info["price"] if isinstance(info["price"], (list, tuple)) else [info["price"], info["price"]]
                    results.append({ "mode": "train", "price": round(prices[0] * adults, 2),
                        "duration_min": int(info["time"][0] * 60), "distance_km": info["distance"][0],
                        "speed_kmh": info.get("speed"), "comfort": 8, "currency": currency,
                        "operator": f"Shortest distance · {adults} adult{'s' if adults > 1 else ''}" })
                    if info["time"][1] != info["time"][0]:
                        results.append({ "mode": "train", "price": round(prices[1] * adults, 2),
                            "duration_min": int(info["time"][1] * 60), "distance_km": info["distance"][1],
                            "speed_kmh": info.get("speed"), "comfort": 8, "currency": currency,
                            "operator": f"Fastest route · {adults} adult{'s' if adults > 1 else ''}"})
            except Exception as e:
                print(f"[Train] {e}")

        self.results = [r for r in results if p_min <= r["price"] <= p_max]
        self.graphs.results = self.results
        self.after(0, self._on_search_done)

    def _on_search_done(self):
        n = len(self.results)
        self.search_status.config(
            text=f"✓ {n} offer{'s' if n != 1 else ''} found.",
            fg=C["ok"] if n else C["err"])
        self._render_results()
        if self.graphs.HAS_MPL:
            self.graphs._update_stats()

    # =========================================================================
    #  TAB 2 – HOTELS
    # =========================================================================

    def _build_hotel_tab(self, parent):
        sidebar = tk.Frame(parent, bg=C["panel"], width=330)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        vsep(parent).pack(side="left", fill="y")
        right = tk.Frame(parent, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        self._build_hotel_search(sidebar)
        self._build_hotel_results(right)

    def _build_hotel_search(self, parent):
        lbl(parent, "  Hotel Search", font=FH, fg=C["accent4"], bg=C["panel"]).pack(anchor="w", pady=(14, 2), padx=10)
        hsep(parent)

        f = tk.Frame(parent, bg=C["panel"], padx=14)
        f.pack(fill="x", pady=6)
        f.columnconfigure(1, weight=1)

        W = 15

        lbl(f, "City", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_hotel_city = AutocompleteEntry(f, CITY_SUGGESTIONS, width=W)
        self.entry_hotel_city.grid(row=0, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Check-in", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=1, column=0, sticky="w", pady=5)
        self.var_checkin = tk.StringVar()
        ci_w, _ = outlined_date(f, self.var_checkin, width=W)
        ci_w.grid(row=1, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Check-out", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=2, column=0, sticky="w", pady=5)
        self.var_checkout = tk.StringVar()
        co_w, _ = outlined_date(f, self.var_checkout, width=W)
        co_w.grid(row=2, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Adults", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=3, column=0, sticky="w", pady=5)
        self.var_h_adults = tk.StringVar(value="1")
        styled_combo(f, ["1", "2", "3", "4"], self.var_h_adults, width=W).grid(row=3, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Stars", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=4, column=0, sticky="w", pady=5)
        self.var_stars = tk.StringVar(value="Any")
        styled_combo(f, ["Any", "1", "2", "3", "4", "5"], self.var_stars, width=W).grid(row=4, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Rooms", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=5, column=0, sticky="w", pady=5)
        self.var_rooms = tk.StringVar(value="1")
        styled_combo(f, ["1", "2", "3", "4"], self.var_rooms, width=W).grid(row=5, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Board", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=6, column=0, sticky="w", pady=5)
        self.var_board = tk.StringVar(value="Any")
        styled_combo(f, ["Any", "ROOM_ONLY", "BREAKFAST", "HALF_BOARD", "FULL_BOARD", "ALL_INCLUSIVE"],
                     self.var_board, width=W).grid(row=6, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Radius (km)", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=7, column=0, sticky="w", pady=5)
        self.var_radius = tk.StringVar(value="5")
        styled_combo(f, ["1", "2", "5", "10", "20", "50"], self.var_radius, width=W).grid(row=7, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Currency", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=8, column=0, sticky="w", pady=5)
        self.var_h_currency = tk.StringVar(value="EUR")
        styled_combo(f, ["EUR", "RON", "USD", "GBP"], self.var_h_currency, width=W).grid(row=8, column=1, sticky="ew", pady=5, padx=(6, 0))

        hsep(parent)
        action_btn(parent, "  🏨  Search Hotels", self._run_hotel_search, color=C["accent4"], fg="white", width=28).pack(pady=12, padx=14)
        self.hotel_status = lbl(parent, "", font=FS, fg=C["subtext"], bg=C["panel"])
        self.hotel_status.pack(pady=(0, 8))

    def _build_hotel_results(self, parent):
        lbl(parent, "  Hotel Results", font=FH, fg=C["accent4"], bg=C["bg"]).pack(anchor="w", pady=(10, 2), padx=14)
        hsep(parent, padx=14, pady=0)

        container = tk.Frame(parent, bg=C["bg"])
        container.pack(fill="both", expand=True, padx=14, pady=6)

        canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.hotel_frame = tk.Frame(canvas, bg=C["bg"])
        hw = canvas.create_window((0, 0), window=self.hotel_frame, anchor="nw")
        self.hotel_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(hw, width=e.width))

        lbl(self.hotel_frame, "Search for hotels using the panel on the left.", font=FB, fg=C["subtext"], bg=C["bg"]).pack(pady=50)

    def _run_hotel_search(self):
        city = self.entry_hotel_city.get().strip()
        checkin = self.var_checkin.get().strip()
        checkout = self.var_checkout.get().strip()
        if not city or not checkin or not checkout:
            messagebox.showwarning("Missing input", "Please fill in city, check-in, and check-out.")
            return
        self.hotel_status.config(text="Searching…", fg=C["accent1"])
        Thread(target=self._fetch_hotels,
               args=(city, checkin, checkout), daemon=True).start()

    def _fetch_hotels(self, city, checkin, checkout):
        adults = int(self.var_h_adults.get() or 1)
        stars = self.var_stars.get()
        ratings = None if stars == "Any" else int(stars)
        rooms = int(self.var_rooms.get() or 1)
        board = self.var_board.get()
        board_val = None if board == "Any" else board
        radius = int(self.var_radius.get() or 5)
        currency = self.var_h_currency.get()
        try:
            info = self.hotel_svc.get_hotel_info( check_in=checkin, check_out=checkout, address=city, ratings=ratings, adults=adults, currency=currency, room_quantity=rooms, board_type=board_val, radius=radius ) if self.hotel_svc else None
        except Exception as e:
            print(f"[Hotel] {e}")
            info = None
        self.hotel_results = info
        self.after(0, self._on_hotel_done)

    def _on_hotel_done(self):
        info = self.hotel_results
        for w in self.hotel_frame.winfo_children():
            w.destroy()
        if not info or not info.get("name_list"):
            self.hotel_status.config(text="No hotels found.", fg=C["err"])
            lbl(self.hotel_frame, "No hotels found for the given criteria.", font=FB, fg=C["subtext"], bg=C["bg"]).pack(pady=50)
            return

        cur = self.var_h_currency.get()
        self.hotel_status.config(text=f"✓ {info['hotels_found']} hotel(s) · avg {cur} {info['price']:.2f}/night", fg=C["ok"])
        if isinstance(info, list) and len(info) > 0:
            info = info[0]

        names = info.get("name_list", [])
        prices = info.get("price_list", [])
        contacts = info.get("contact_list", [])
        room_descs = info.get("room_description", [])
        room_cats = info.get("room_category", [])
        bed_types = info.get("bed_type", [])
        bed_numbers = info.get("bed_number", [])
        print(type(info))
        print(info)

        def _safe(lst, i, default="—"):
            return lst[i] if lst and i < len(lst) and lst[i] else default

        for i, (name, price) in enumerate(zip(names, prices)):
            bg = C["card"] if i % 2 == 0 else C["card_alt"]
            card = tk.Frame(self.hotel_frame, bg=bg, pady=10, highlightthickness=1, highlightbackground=C["border"])
            card.pack(fill="x", pady=4)
            tk.Frame(card, bg=C["accent4"], width=5).pack(side="left", fill="y")
            inner = tk.Frame(card, bg=bg, padx=12)
            inner.pack(side="left", fill="both", expand=True)

            # ── Name and price ──────────────────────────
            row = tk.Frame(inner, bg=bg)
            row.pack(fill="x")
            lbl(row, f"🏨  {name}", font=FH, fg=C["accent4"], bg=bg).pack(side="left")
            lbl(row, f"{cur} {price:.2f} / night", font=("Segoe UI", 11, "bold"), fg=C["text"], bg=bg).pack(side="right")

            # ── Contact ───────────────────────────────
            contact = _safe(contacts, i)
            lbl(inner, f"📞  {contact}", font=FS, fg=C["subtext"], bg=bg).pack(anchor="w", pady=(2, 0))

            # ── Room details ──────────────────────────
            room_det = tk.Frame(inner, bg=bg)
            room_det.pack(fill="x", pady=(2, 0))
            det_items = []
            rd = _safe(room_descs, i, "")
            rc = _safe(room_cats, i, "")
            bt = _safe(bed_types, i, "")
            bn = _safe(bed_numbers, i, "")
            if rc and rc != "—":
                det_items.append(f"🛏 {rc}")
            if rd and rd != "—":
                det_items.append(f"📋 {rd}")
            if bt and bt != "—":
                bed_txt = f"{bn}× {bt}" if bn and bn != "—" else bt
                det_items.append(f"🛌 {bed_txt}")
            for t in det_items:
                lbl(room_det, t, font=FS, fg=C["subtext"], bg=bg).pack(side="left", padx=(0, 12))

if __name__ == "__main__":
    app = TravelApp()
    app.mainloop()
