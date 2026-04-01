import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread

try:
    from tkcalendar import Calendar
    from tkcalendar import DateEntry
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

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

# ─── Light palette ────────────────────────────────────────────────────────────
C = {
    "bg":       "#F4F7FB",
    "panel":    "#FFFFFF",
    "card":     "#FFFFFF",
    "card_alt": "#F0F5FB",
    "input":    "#FFFFFF",
    "input_bd": "#ADC0D4",
    "accent1":  "#1A6FC4",
    "accent2":  "#D05A10",
    "accent3":  "#2A8C3F",
    "accent4":  "#B07800",
    "text":     "#1C2B3A",
    "subtext":  "#6B7F94",
    "border":   "#D0DCE8",
    "ok":       "#2A8C3F",
    "warn":     "#D05A10",
    "err":      "#C0253A",
    "hdr_bg":   "#1A3A5C",
    "hdr_fg":   "#E8F4FF",
}

MODE_COLOR = {"flight": C["accent1"], "car": C["accent2"], "train": C["accent3"]}
MODE_ICON  = {"flight": "✈", "car": "🚗", "train": "🚆"}

CITY_SUGGESTIONS = sorted([
    "Amsterdam","Athens","Barcelona","Berlin","Brașov","Bucharest",
    "Budapest","Cluj-Napoca","Copenhagen","Dublin","Frankfurt",
    "Geneva","Hamburg","Helsinki","Iași","Istanbul","Lisbon",
    "London","Luxembourg","Lyon","Madrid","Milan","Munich",
    "Nice","Oslo","Paris","Prague","Rome","Rotterdam",
    "Sofia","Stockholm","Timișoara","Vienna","Warsaw","Zurich",
])

FT  = ("Segoe UI", 18, "bold")
FH  = ("Segoe UI", 11, "bold")
FB  = ("Segoe UI", 10)
FS  = ("Segoe UI", 9)
FSB = ("Segoe UI", 9, "bold")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def lbl(parent, text, font=None, fg=None, bg=None, **kw):
    return tk.Label(parent, text=text, font=font or FB,
                    fg=fg or C["text"], bg=bg or C["panel"], **kw)

def hsep(parent, padx=10, pady=4):
    tk.Frame(parent, height=1, bg=C["border"]).pack(fill="x", padx=padx, pady=pady)

def vsep(parent):
    return tk.Frame(parent, width=1, bg=C["border"])

def action_btn(parent, text, command, color=None, fg="white", width=None):
    b = tk.Button(parent, text=text, command=command,
                  font=FSB, fg=fg, bg=color or C["accent1"],
                  activebackground="#0F4A8A", activeforeground="white",
                  relief="flat", bd=0, padx=14, pady=7, cursor="hand2")
    if width:
        b.config(width=width)
    return b

def styled_combo(parent, values, textvariable=None, width=14):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("L.TCombobox",
                    fieldbackground=C["input"], background=C["input"],
                    foreground=C["text"], arrowcolor=C["accent1"],
                    bordercolor=C["input_bd"], lightcolor=C["input_bd"],
                    darkcolor=C["input_bd"],
                    selectbackground=C["accent1"], selectforeground="white")
    return ttk.Combobox(parent, values=values, textvariable=textvariable,
                        width=width, font=FB, state="readonly", style="L.TCombobox")

def outlined_date(parent, textvariable=None, width=14):
    wrap = tk.Frame(parent, bg=C["input_bd"], padx=1, pady=1)

    if HAS_CALENDAR:
        from datetime import date
        d = DateEntry( wrap,
            textvariable=textvariable,
            font=FB,
            background=C["accent1"],     # header calendar
            foreground="white",
            normalbackground=C["input"], # input field
            normalforeground=C["text"],
            borderwidth=0,
            date_pattern="yyyy-mm-dd",
            mindate=date.today(),
            width=width,
            showweeknumbers=False
        )
        d.pack(fill="x", padx=2, pady=2)
        return wrap, d
    else:
        e = tk.Entry(
            wrap,
            textvariable=textvariable,
            width=width,
            font=FB,
            fg=C["text"],
            bg=C["input"],
            insertbackground=C["accent1"],
            relief="flat",
            bd=4,
            highlightthickness=0
        )
        e.pack(fill="x")
        return wrap, e

def fmt_time(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"

# ─── Autocomplete Entry ───────────────────────────────────────────────────────

class AutocompleteEntry(tk.Frame):
    def __init__(self, parent, suggestions, textvariable=None, width=18, **kw):
        super().__init__(parent, bg=C["input_bd"], padx=1, pady=1)
        self.suggestions = suggestions
        self.var = textvariable or tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, width=width,
                              font=FB, fg=C["text"], bg=C["input"],
                              insertbackground=C["accent1"],
                              relief="flat", bd=4, highlightthickness=0)
        self.entry.pack(fill="x")
        self._win = None
        self._lb  = None
        self.var.trace_add("write", self._on_type)
        self.entry.bind("<FocusOut>", lambda e: self.after(150, self._hide))
        self.entry.bind("<Escape>",   lambda e: self._hide())
        self.entry.bind("<Return>",   lambda e: self._hide())
        self.entry.bind("<Down>",     self._focus_list)

    def get(self):
        return self.var.get()

    def _on_type(self, *_):
        typed = self.var.get().strip().lower()
        if not typed:
            self._hide(); return
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
        h = min(len(matches)*22+4, 180)
        self._win = tk.Toplevel(self)
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(f"{w}x{h}+{x}+{y}")
        self._win.lift()
        self._lb = tk.Listbox(self._win, font=FB, fg=C["text"],
                              bg=C["panel"], selectbackground=C["accent1"],
                              selectforeground="white", relief="flat", bd=0,
                              activestyle="none", highlightthickness=1,
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

# ─── Dual Range Slider ────────────────────────────────────────────────────────

class DualRangeSlider(tk.Frame):
    def __init__(self, parent, min_val=0, max_val=2000):
        super().__init__(parent, bg=C["panel"])
        self.var_min = tk.IntVar(value=min_val)
        self.var_max = tk.IntVar(value=max_val)

        sk = dict(orient="horizontal", from_=0, to=max_val,
                  bg=C["panel"], fg=C["text"], troughcolor=C["border"],
                  highlightthickness=0, activebackground=C["accent1"],
                  font=FS, length=220, showvalue=False)

        r1 = tk.Frame(self, bg=C["panel"]); r1.pack(fill="x")
        lbl(r1, "Min €", font=FS, fg=C["subtext"], bg=C["panel"]).pack(side="left")
        self.lbl_min = lbl(r1, "0", font=FSB, fg=C["accent1"], bg=C["panel"])
        self.lbl_min.pack(side="right")
        tk.Scale(self, variable=self.var_min, command=self._on_min, **sk).pack(fill="x")

        r2 = tk.Frame(self, bg=C["panel"]); r2.pack(fill="x")
        lbl(r2, "Max €", font=FS, fg=C["subtext"], bg=C["panel"]).pack(side="left")
        self.lbl_max = lbl(r2, str(max_val), font=FSB, fg=C["accent1"], bg=C["panel"])
        self.lbl_max.pack(side="right")
        s2 = tk.Scale(self, variable=self.var_max, command=self._on_max, **sk)
        s2.set(max_val); s2.pack(fill="x")

    def _on_min(self, val):
        if int(float(val)) > self.var_max.get():
            self.var_min.set(self.var_max.get())
        self.lbl_min.config(text=str(self.var_min.get()))

    def _on_max(self, val):
        if int(float(val)) < self.var_min.get():
            self.var_max.set(self.var_min.get())
        self.lbl_max.config(text=str(self.var_max.get()))

    def get(self):
        return self.var_min.get(), self.var_max.get()

# ─── Main App ─────────────────────────────────────────────────────────────────

class TravelApp(tk.Tk):
    def __init__(self):
        super().__init__()
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
            self.hotel_svc  = HotelService(client)
        except Exception:
            pass
        try:
            self.car_svc   = CarService()
            self.train_svc = TrainService()
        except Exception:
            pass

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        h = tk.Frame(self, bg=C["hdr_bg"], pady=11)
        h.pack(fill="x")
        lbl(h, "  ✈  TRAVEL OFFER MANAGER", font=FT,
            fg=C["hdr_fg"], bg=C["hdr_bg"]).pack(side="left", padx=20)
        status = "● Backend connected" if BACKEND_AVAILABLE else "● Demo mode"
        scol   = C["ok"] if BACKEND_AVAILABLE else C["warn"]
        lbl(h, status + "  ", font=FS, fg=scol,
            bg=C["hdr_bg"]).pack(side="right", padx=16)

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _build_tabs(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TNotebook",
                        background=C["bg"], borderwidth=0, tabmargins=0)
        style.configure("App.TNotebook.Tab",
                        background=C["border"], foreground=C["subtext"],
                        font=FH, padding=[20, 8], borderwidth=0)
        style.map("App.TNotebook.Tab",
                  background=[("selected", C["panel"])],
                  foreground=[("selected", C["accent1"])])

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
        self._build_stats_tab(t3)

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
        lbl(parent, "  Search", font=FH, fg=C["accent1"],
            bg=C["panel"]).pack(anchor="w", pady=(14, 2), padx=10)
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

        # ── FORM ──────────────────────────────────────
        f = tk.Frame(inner, bg=C["panel"], padx=14)
        f.pack(fill="x", pady=4)
        f.columnconfigure(1, weight=1)

        lbl(f, "From", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_origin = AutocompleteEntry(f, CITY_SUGGESTIONS, width=17)
        self.entry_origin.grid(row=0, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "To", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_dest = AutocompleteEntry(f, CITY_SUGGESTIONS, width=17)
        self.entry_dest.grid(row=1, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Departure date", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=2, column=0, sticky="w", pady=5)
        self.var_depart = tk.StringVar()
        dw, _ = outlined_date(f, self.var_depart, width=14)
        dw.grid(row=2, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Return date", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=3, column=0, sticky="w", pady=5)
        self.var_return = tk.StringVar()
        rw, _ = outlined_date(f, self.var_return, width=14)
        rw.grid(row=3, column=1, sticky="ew", pady=5, padx=(6, 0))

        lbl(f, "Adults", bg=C["panel"], fg=C["subtext"], font=FS).grid(row=4, column=0, sticky="w", pady=5)
        self.var_adults = tk.StringVar(value="1")
        styled_combo(f, ["1", "2", "3", "4", "5", "6"], self.var_adults, width=5) \
            .grid(row=4, column=1, sticky="w", pady=5, padx=(6, 0))

        hsep(inner)

        # ── Fuel (dinamic) ────────────────────────────
        self.fuel_container = tk.Frame(inner, bg=C["panel"], padx=14)

        lbl(self.fuel_container, "Car fuel type", font=FSB, bg=C["panel"]) \
            .pack(anchor="w", pady=(4, 2))

        self.var_fuel = tk.StringVar(value="diesel")

        for fuel in ["gasoline", "diesel", "LPG"]:
            tk.Radiobutton(
                self.fuel_container,
                text=fuel,
                variable=self.var_fuel,
                value=fuel,
                font=FS,
                fg=C["text"],
                bg=C["panel"],
                selectcolor=C["accent2"],
                activebackground=C["panel"],
                activeforeground=C["accent2"]
            ).pack(anchor="w")

        hsep(inner)

        # ── Transport modes ───────────────────────────
        f4 = tk.Frame(inner, bg=C["panel"], padx=14)
        f4.pack(fill="x", pady=2)

        lbl(f4, "Transport modes", font=FSB, bg=C["panel"]).pack(anchor="w", pady=(4, 2))

        self.var_flight = tk.BooleanVar(value=True)
        self.var_car = tk.BooleanVar(value=True)
        self.var_train = tk.BooleanVar(value=True)

        def styled_check(parent, text, var):
            return tk.Checkbutton(
                parent,
                text=text,
                variable=var,
                font=FB,
                fg=C["text"],
                bg=C["panel"],
                activebackground=C["panel"],
                activeforeground=C["text"],
                selectcolor="white",
                highlightthickness=1,
                highlightbackground=C["border"],
                indicatoron=True,
                padx=6,
                pady=4
            )

        styled_check(f4, "✈  Plane", self.var_flight).pack(anchor="w", pady=2)

        self.chk_car = styled_check(f4, "🚗  Car", self.var_car)
        self.chk_car.pack(anchor="w", pady=2)

        styled_check(f4, "🚆  Train", self.var_train).pack(anchor="w", pady=2)

        # ── Toggle fuel ───────────────────────────────
        def toggle_fuel(*args):
            if self.var_car.get():
                self.fuel_container.pack(fill="x", pady=2)
            else:
                self.fuel_container.pack_forget()

        self.var_car.trace_add("write", toggle_fuel)
        toggle_fuel()

        hsep(inner)

        # ── Price ─────────────────────────────────────
        f3 = tk.Frame(inner, bg=C["panel"], padx=14)
        f3.pack(fill="x", pady=2)

        lbl(f3, "Price range (€)", font=FSB, bg=C["panel"]).pack(anchor="w", pady=(4, 4))
        self.price_range = DualRangeSlider(f3)
        self.price_range.pack(fill="x")

        hsep(inner)

        action_btn(inner, "  🔍  Find Best Offers", self._run_search,
                   color=C["accent1"], width=30).pack(pady=12, padx=14)

        self.search_status = lbl(inner, "", font=FS,
                                 fg=C["subtext"], bg=C["panel"])
        self.search_status.pack(pady=(0, 10))

    def _build_results_panel(self, parent):
        top = tk.Frame(parent, bg=C["bg"])
        top.pack(fill="x", padx=14, pady=(10,4))
        lbl(top, "Results", font=FH, fg=C["accent1"], bg=C["bg"]).pack(side="left")

        sort_f = tk.Frame(top, bg=C["bg"]); sort_f.pack(side="right")
        lbl(sort_f, "Sort by:", font=FS, fg=C["subtext"], bg=C["bg"]).pack(side="left", padx=(0,4))
        self.var_sort = tk.StringVar(value="price")
        for label, val in [("Price","price"),("Duration","duration"),
                            ("Comfort","comfort"),("Best Overall","overall")]:
            tk.Radiobutton(sort_f, text=label, variable=self.var_sort,
                           value=val, command=self._render_results,
                           font=FS, fg=C["text"], bg=C["bg"],
                           selectcolor=C["accent1"],
                           activebackground=C["bg"]).pack(side="left", padx=5)

        hsep(parent, padx=14, pady=0)

        container = tk.Frame(parent, bg=C["bg"])
        container.pack(fill="both", expand=True, padx=14, pady=6)

        canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.results_frame = tk.Frame(canvas, bg=C["bg"])
        self._rwin = canvas.create_window((0,0), window=self.results_frame, anchor="nw")
        self.results_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._rwin, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._show_placeholder("Enter origin and destination, then click Find Best Offers.")

    def _show_placeholder(self, msg):
        for w in self.results_frame.winfo_children():
            w.destroy()
        lbl(self.results_frame, msg, font=FB, fg=C["subtext"], bg=C["bg"]).pack(pady=50)

    def _overall_score(self, r):
        prices   = [x["price"]        for x in self.results] or [1]
        durations= [x["duration_min"] for x in self.results] or [1]
        rng_p = max(prices)   - min(prices)   or 1
        rng_d = max(durations)- min(durations) or 1
        p_n = (r["price"]        - min(prices))   / rng_p
        d_n = (r["duration_min"] - min(durations))/ rng_d
        c_n = 1 - (r.get("comfort",5) - 1) / 9
        return p_n*0.4 + d_n*0.35 + c_n*0.25

    def _render_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        if not self.results:
            self._show_placeholder("No offers found for the selected criteria.")
            return
        key_map = {
            "price":    lambda r: r["price"],
            "duration": lambda r: r["duration_min"],
            "comfort":  lambda r: -r.get("comfort",5),
            "overall":  self._overall_score,
        }
        sorted_res = sorted(self.results,
                            key=key_map.get(self.var_sort.get(), key_map["price"]))
        best_price = min(r["price"] for r in sorted_res)
        for i, offer in enumerate(sorted_res):
            self._render_card(offer, i, offer["price"] == best_price)

    def _render_card(self, offer, idx, is_best):
        mode  = offer["mode"]
        color = MODE_COLOR.get(mode, C["accent1"])
        icon  = MODE_ICON.get(mode, "?")
        bg    = C["card"] if idx%2==0 else C["card_alt"]

        card = tk.Frame(self.results_frame, bg=bg, pady=10,
                        highlightthickness=1,
                        highlightbackground=C["accent4"] if is_best else C["border"])
        card.pack(fill="x", pady=4)

        tk.Frame(card, bg=color, width=5).pack(side="left", fill="y")
        inner = tk.Frame(card, bg=bg, padx=12)
        inner.pack(side="left", fill="both", expand=True)

        top = tk.Frame(inner, bg=bg); top.pack(fill="x")
        lbl(top, f"{icon}  {mode.upper()}", font=FH, fg=color, bg=bg).pack(side="left")
        if is_best:
            lbl(top, "  ★ Best Price", font=FSB, fg=C["accent4"], bg=bg).pack(side="left", padx=6)
        lbl(top, f"€ {offer['price']:.2f}",
            font=("Segoe UI",12,"bold"), fg=C["text"], bg=bg).pack(side="right")

        det = tk.Frame(inner, bg=bg); det.pack(fill="x", pady=(3,0))
        items = [
            f"⏱ {fmt_time(offer['duration_min'])}",
            f"📍 {offer['distance_km']:.0f} km" if offer.get("distance_km") else "",
            f"🎯 Comfort {offer['comfort']}/10" if offer.get("comfort") else "",
            offer.get("operator",""),
        ]
        for t in items:
            if t.strip():
                lbl(det, t, font=FS, fg=C["subtext"], bg=bg).pack(side="left", padx=(0,12))

    # ── Search logic ──────────────────────────────────────────────────────────

    def _run_search(self):
        origin = self.entry_origin.get().strip()
        dest   = self.entry_dest.get().strip()
        if not origin or not dest:
            messagebox.showwarning("Missing input","Please enter both origin and destination.")
            return
        if origin.lower() == dest.lower():
            messagebox.showwarning("Same city","Origin and destination must be different.")
            return
        self.results = []
        self._show_placeholder("🔄  Searching — please wait…")
        self.search_status.config(text="Fetching offers…", fg=C["accent1"])
        Thread(target=self._fetch_all, args=(origin, dest), daemon=True).start()

    def _fetch_all(self, origin, dest):
        results = []
        depart  = self.var_depart.get()
        ret     = self.var_return.get() or None
        adults  = int(self.var_adults.get() or 1)
        fuel    = self.var_fuel.get()
        p_min, p_max = self.price_range.get()

        if self.var_flight.get() and self.flight_svc:
            try:
                info = self.flight_svc.get_flight_info(origin, dest, depart, ret, adults)
                if info:
                    results.append({"mode":"flight","price":info["price"][0],
                                    "duration_min":info["time"][0],"comfort":6,
                                    "operator":"Cheapest option"})
                    if info["price"][1] != info["price"][0]:
                        results.append({"mode":"flight","price":info["price"][1],
                                        "duration_min":info["time"][1],"comfort":7,
                                        "operator":"Fastest option"})
            except Exception as e:
                print(f"[Flight] {e}")

        if self.var_car.get() and self.car_svc:
            try:
                info = self.car_svc.get_car_info(origin, dest, fuel)
                if info:
                    results.append({"mode":"car","price":round(info["price"],2),
                                    "duration_min":int(info["time"]*60),
                                    "distance_km":info["distance"],"comfort":7,
                                    "operator":f"{fuel.capitalize()} · {info['distance']:.0f} km"})
            except Exception as e:
                print(f"[Car] {e}")

        if self.var_train.get() and self.train_svc:
            try:
                info = self.train_svc.get_train_info(origin, dest)
                if info:
                    results.append({"mode":"train","price":info["price"],
                                    "duration_min":int(info["time"][0]*60),
                                    "distance_km":info["distance"][0],"comfort":8,
                                    "operator":"Shortest distance"})
                    if info["time"][1] != info["time"][0]:
                        results.append({"mode":"train","price":info["price"],
                                        "duration_min":int(info["time"][1]*60),
                                        "distance_km":info["distance"][1],"comfort":8,
                                        "operator":"Fastest route"})
            except Exception as e:
                print(f"[Train] {e}")

        self.results = [r for r in results if p_min <= r["price"] <= p_max]
        self.after(0, self._on_search_done)

    def _on_search_done(self):
        n = len(self.results)
        self.search_status.config(
            text=f"✓ {n} offer{'s' if n!=1 else ''} found.",
            fg=C["ok"] if n else C["err"])
        self._render_results()
        if HAS_MPL:
            self._update_stats()

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
        lbl(parent, "  Hotel Search", font=FH, fg=C["accent4"],
            bg=C["panel"]).pack(anchor="w", pady=(14,2), padx=10)
        hsep(parent)

        f = tk.Frame(parent, bg=C["panel"], padx=14)
        f.pack(fill="x", pady=6)
        f.columnconfigure(1, weight=1)

        W = 15   # uniform widget width for all hotel inputs

        lbl(f, "City", bg=C["panel"], fg=C["subtext"], font=FS).grid(
            row=0, column=0, sticky="w", pady=6)
        self.entry_hotel_city = AutocompleteEntry(f, CITY_SUGGESTIONS, width=W)
        self.entry_hotel_city.grid(row=0, column=1, sticky="ew", pady=6, padx=(6,0))

        lbl(f, "Check-in", bg=C["panel"], fg=C["subtext"], font=FS).grid(
            row=1, column=0, sticky="w", pady=6)
        self.var_checkin = tk.StringVar()
        ci_w, _ = outlined_date(f, self.var_checkin, width=W)
        ci_w.grid(row=1, column=1, sticky="ew", pady=6, padx=(6,0))

        lbl(f, "Check-out", bg=C["panel"], fg=C["subtext"], font=FS).grid(
            row=2, column=0, sticky="w", pady=6)
        self.var_checkout = tk.StringVar()
        co_w, _ = outlined_date(f, self.var_checkout, width=W)
        co_w.grid(row=2, column=1, sticky="ew", pady=6, padx=(6,0))

        # Adults and Stars use the SAME combo width so boxes match
        lbl(f, "Adults", bg=C["panel"], fg=C["subtext"], font=FS).grid(
            row=3, column=0, sticky="w", pady=6)
        self.var_h_adults = tk.StringVar(value="1")
        styled_combo(f, ["1","2","3","4"], self.var_h_adults, width=W).grid(
            row=3, column=1, sticky="ew", pady=6, padx=(6,0))

        lbl(f, "Stars", bg=C["panel"], fg=C["subtext"], font=FS).grid(
            row=4, column=0, sticky="w", pady=6)
        self.var_stars = tk.StringVar(value="Any")
        styled_combo(f, ["Any","1","2","3","4","5"], self.var_stars, width=W).grid(
            row=4, column=1, sticky="ew", pady=6, padx=(6,0))

        hsep(parent)
        action_btn(parent, "  🏨  Search Hotels", self._run_hotel_search,
                   color=C["accent4"], fg="white", width=28).pack(pady=12, padx=14)
        self.hotel_status = lbl(parent, "", font=FS, fg=C["subtext"], bg=C["panel"])
        self.hotel_status.pack(pady=(0,8))

    def _build_hotel_results(self, parent):
        lbl(parent, "  Hotel Results", font=FH, fg=C["accent4"],
            bg=C["bg"]).pack(anchor="w", pady=(10,2), padx=14)
        hsep(parent, padx=14, pady=0)

        container = tk.Frame(parent, bg=C["bg"])
        container.pack(fill="both", expand=True, padx=14, pady=6)

        canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.hotel_frame = tk.Frame(canvas, bg=C["bg"])
        hw = canvas.create_window((0,0), window=self.hotel_frame, anchor="nw")
        self.hotel_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(hw, width=e.width))

        lbl(self.hotel_frame, "Search for hotels using the panel on the left.",
            font=FB, fg=C["subtext"], bg=C["bg"]).pack(pady=50)

    def _run_hotel_search(self):
        city    = self.entry_hotel_city.get().strip()
        checkin = self.var_checkin.get().strip()
        checkout= self.var_checkout.get().strip()
        if not city or not checkin or not checkout:
            messagebox.showwarning("Missing input",
                                   "Please fill in city, check-in, and check-out.")
            return
        self.hotel_status.config(text="Searching…", fg=C["accent1"])
        Thread(target=self._fetch_hotels,
               args=(city,checkin,checkout), daemon=True).start()

    def _fetch_hotels(self, city, checkin, checkout):
        adults  = int(self.var_h_adults.get() or 1)
        stars   = self.var_stars.get()
        ratings = None if stars=="Any" else int(stars)
        try:
            info = self.hotel_svc.get_hotel_info(
                check_in=checkin, check_out=checkout,
                address=city, ratings=ratings, adults=adults
            ) if self.hotel_svc else None
        except Exception as e:
            print(f"[Hotel] {e}"); info = None
        self.hotel_results = info
        self.after(0, self._on_hotel_done)

    def _on_hotel_done(self):
        info = self.hotel_results
        for w in self.hotel_frame.winfo_children():
            w.destroy()
        if not info or not info.get("name_list"):
            self.hotel_status.config(text="No hotels found.", fg=C["err"])
            lbl(self.hotel_frame, "No hotels found for the given criteria.",
                font=FB, fg=C["subtext"], bg=C["bg"]).pack(pady=50)
            return
        self.hotel_status.config(
            text=f"✓ {info['hotels_found']} hotel(s) · avg €{info['price']:.2f}/night",
            fg=C["ok"])
        for i,(name,price) in enumerate(zip(info["name_list"],info["price_list"])):
            contact = (info["contact_list"][i]
                       if i<len(info["contact_list"]) and info["contact_list"][i] else "—")
            bg = C["card"] if i%2==0 else C["card_alt"]
            card = tk.Frame(self.hotel_frame, bg=bg, pady=10,
                            highlightthickness=1, highlightbackground=C["border"])
            card.pack(fill="x", pady=4)
            tk.Frame(card, bg=C["accent4"], width=5).pack(side="left", fill="y")
            inner = tk.Frame(card, bg=bg, padx=12)
            inner.pack(side="left", fill="both", expand=True)
            row = tk.Frame(inner, bg=bg); row.pack(fill="x")
            lbl(row, f"🏨  {name}", font=FH, fg=C["accent4"], bg=bg).pack(side="left")
            lbl(row, f"€ {price:.2f} / night",
                font=("Segoe UI",11,"bold"), fg=C["text"], bg=bg).pack(side="right")
            lbl(inner, f"📞  {contact}", font=FS, fg=C["subtext"], bg=bg).pack(anchor="w", pady=2)

    # =========================================================================
    #  TAB 3 – STATISTICS
    # =========================================================================

    def _build_stats_tab(self, parent):
        lbl(parent, "  Statistics", font=FH, fg=C["accent1"],
            bg=C["bg"]).pack(anchor="w", pady=(12,2), padx=14)
        hsep(parent, padx=14, pady=0)
        if not HAS_MPL:
            lbl(parent, "Install matplotlib:\n  pip install matplotlib",
                font=FB, fg=C["warn"], bg=C["bg"]).pack(pady=40)
            return
        self.stats_frame = tk.Frame(parent, bg=C["bg"])
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self._update_stats()

    def _update_stats(self):
        if not HAS_MPL or not hasattr(self, "stats_frame"):
            return
        for w in self.stats_frame.winfo_children():
            w.destroy()
        if not self.results:
            lbl(self.stats_frame, "Run a travel search first to see statistics.",
                font=FB, fg=C["subtext"], bg=C["bg"]).pack(pady=50)
            return

        modes     = [r["mode"]          for r in self.results]
        prices    = [r["price"]         for r in self.results]
        durations = [r["duration_min"]  for r in self.results]
        bar_lbl   = [f"{MODE_ICON[m]}\n{m}\n€{p:.0f}" for m,p in zip(modes,prices)]
        colors    = [MODE_COLOR[m] for m in modes]

        fig = Figure(figsize=(11, 7), facecolor=C["bg"])
        fig.subplots_adjust(hspace=0.5, wspace=0.35)

        # 1 – Price bar
        ax1 = fig.add_subplot(2,2,1)
        ax1.set_facecolor(C["card_alt"])
        bars = ax1.bar(bar_lbl, prices, color=colors, width=0.55,
                       edgecolor="white", linewidth=0.5)
        for bar,p in zip(bars,prices):
            ax1.text(bar.get_x()+bar.get_width()/2,
                     bar.get_height()+max(prices)*0.01,
                     f"€{p:.0f}", ha="center", va="bottom",
                     color=C["text"], fontsize=8)
        ax1.set_title("Price Comparison (€)", color=C["text"], fontsize=10, pad=8)
        ax1.tick_params(colors=C["subtext"], labelsize=7)
        ax1.spines[:].set_color(C["border"])
        ax1.set_ylabel("EUR", color=C["subtext"], fontsize=8)

        # 2 – Travel time horizontal bar
        ax2 = fig.add_subplot(2,2,2)
        ax2.set_facecolor(C["card_alt"])
        dur_h = [d/60 for d in durations]
        bars2 = ax2.barh(bar_lbl, dur_h, color=colors,
                         edgecolor="white", linewidth=0.5)
        for bar,d in zip(bars2,durations):
            ax2.text(bar.get_width()+0.04, bar.get_y()+bar.get_height()/2,
                     fmt_time(d), va="center", color=C["text"], fontsize=8)
        ax2.set_title("Travel Time", color=C["text"], fontsize=10, pad=8)
        ax2.tick_params(colors=C["subtext"], labelsize=7)
        ax2.spines[:].set_color(C["border"])
        ax2.set_xlabel("Hours", color=C["subtext"], fontsize=8)

        # 3 – Price vs Comfort
        ax3 = fig.add_subplot(2,2,3)
        ax3.set_facecolor(C["card_alt"])
        for r in self.results:
            ax3.scatter(r["price"], r.get("comfort",5),
                        color=MODE_COLOR[r["mode"]], s=140,
                        edgecolors="white", linewidths=0.5, zorder=3)
            ax3.annotate(MODE_ICON[r["mode"]],
                         (r["price"], r.get("comfort",5)),
                         textcoords="offset points", xytext=(5,3),
                         color=MODE_COLOR[r["mode"]], fontsize=11)
        ax3.set_title("Price vs Comfort", color=C["text"], fontsize=10, pad=8)
        ax3.set_xlabel("Price (€)", color=C["subtext"], fontsize=8)
        ax3.set_ylabel("Comfort (1–10)", color=C["subtext"], fontsize=8)
        ax3.tick_params(colors=C["subtext"], labelsize=7)
        ax3.spines[:].set_color(C["border"])
        ax3.set_ylim(0,11)
        ax3.grid(color=C["border"], linewidth=0.5, alpha=0.6)

        # 4 – Mode pie
        ax4 = fig.add_subplot(2,2,4)
        ax4.set_facecolor(C["bg"])
        mc = {}
        for m in modes: mc[m] = mc.get(m,0)+1
        ax4.pie(list(mc.values()),
                labels=[f"{MODE_ICON[m]} {m}" for m in mc],
                colors=[MODE_COLOR[m] for m in mc],
                autopct="%1.0f%%",
                textprops={"color":C["text"],"fontsize":9},
                wedgeprops={"edgecolor":C["bg"],"linewidth":2})
        ax4.set_title("Offers by Mode", color=C["text"], fontsize=10, pad=8)

        canvas = FigureCanvasTkAgg(fig, master=self.stats_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    app = TravelApp()
    app.mainloop()
