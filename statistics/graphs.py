import tkinter as tk
from utils.interface import *
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class Graphs:
    def __init__(self):
        try:
            matplotlib.use("TkAgg")
            self.HAS_MPL = True
        except ImportError:

            self.HAS_MPL = False
        self.results = []


    def _build_stats_tab(self, parent):
        lbl(parent, "  Statistics", font=FH, fg=C["accent1"], bg=C["bg"]).pack(anchor="w", pady=(12, 2), padx=14)
        hsep(parent, padx=14, pady=0)
        if not self.HAS_MPL:
            lbl(parent, "Install matplotlib:\n  pip install matplotlib", font=FH, fg=C["warn"], bg=C["bg"]).pack(pady=40)
            return
        self.stats_frame = tk.Frame(parent, bg=C["bg"])
        self.stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self._update_stats()


    def _update_stats(self):
        if not self.HAS_MPL or not hasattr(self, "stats_frame"):
            return
        for w in self.stats_frame.winfo_children():
            w.destroy()
        if not self.results:
            lbl(self.stats_frame, "Run a travel search first to see statistics.", font=FH, fg=C["subtext"],
                bg=C["bg"]).pack(pady=50)
            return

        modes = [r["mode"] for r in self.results]
        prices = [r["price"] for r in self.results]
        durations = [r["duration_min"] for r in self.results]
        bar_lbl = [f"{MODE_ICON[m]}\n{m}\n€{p:.0f}" for m, p in zip(modes, prices)]
        colors = [MODE_COLOR[m] for m in modes]

        fig = Figure(figsize=(11, 7), facecolor=C["bg"])
        fig.subplots_adjust(hspace=0.5, wspace=0.35)

        # 1 – Price bar
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.set_facecolor(C["card_alt"])
        bars = ax1.bar(bar_lbl, prices, color=colors, width=0.55, edgecolor="white", linewidth=0.5)
        for bar, p in zip(bars, prices):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(prices) * 0.01, f"€{p:.0f}", ha="center",
                     va="bottom", color=C["text"], fontsize=8)
        ax1.set_title("Price Comparison (€)", color=C["text"], fontsize=10, pad=8)
        ax1.tick_params(colors=C["subtext"], labelsize=7)
        ax1.spines[:].set_color(C["border"])
        ax1.set_ylabel("EUR", color=C["subtext"], fontsize=8)

        # 2 – Travel time horizontal bar
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.set_facecolor(C["card_alt"])
        dur_h = [d / 60 for d in durations]
        bars2 = ax2.barh(bar_lbl, dur_h, color=colors, edgecolor="white", linewidth=0.5)
        for bar, d in zip(bars2, durations):
            ax2.text(bar.get_width() + 0.04, bar.get_y() + bar.get_height() / 2, fmt_time(d), va="center", color=C["text"],
                     fontsize=8)
        ax2.set_title("Travel Time", color=C["text"], fontsize=10, pad=8)
        ax2.tick_params(colors=C["subtext"], labelsize=7)
        ax2.spines[:].set_color(C["border"])
        ax2.set_xlabel("Hours", color=C["subtext"], fontsize=8)

        # 3 – Price vs. Comfort
        ax3 = fig.add_subplot(2, 2, 3)
        ax3.set_facecolor(C["card_alt"])
        for r in self.results:
            ax3.scatter(r["price"], r.get("comfort", 5), color=MODE_COLOR[r["mode"]], s=140, edgecolors="white",
                        linewidths=0.5, zorder=3)
            ax3.annotate(MODE_ICON[r["mode"]], (r["price"], r.get("comfort", 5)), textcoords="offset points", xytext=(5, 3),
                         color=MODE_COLOR[r["mode"]], fontsize=11)
        ax3.set_title("Price vs Comfort", color=C["text"], fontsize=10, pad=8)
        ax3.set_xlabel("Price (€)", color=C["subtext"], fontsize=8)
        ax3.set_ylabel("Comfort (1–10)", color=C["subtext"], fontsize=8)
        ax3.tick_params(colors=C["subtext"], labelsize=7)
        ax3.spines[:].set_color(C["border"])
        ax3.set_ylim(0, 11)
        ax3.grid(color=C["border"], linewidth=0.5, alpha=0.6)

        # 4 – Mode pie
        ax4 = fig.add_subplot(2, 2, 4)
        ax4.set_facecolor(C["bg"])
        mc = {}
        for m in modes:
            mc[m] = mc.get(m, 0) + 1
        ax4.pie(list(mc.values()), labels=[f"{MODE_ICON[m]} {m}" for m in mc], colors=[MODE_COLOR[m] for m in mc],
                autopct="%1.0f%%", textprops={"color": C["text"], "fontsize": 9},
                wedgeprops={"edgecolor": C["bg"], "linewidth": 2})
        ax4.set_title("Offers by Mode", color=C["text"], fontsize=10, pad=8)

        canvas = FigureCanvasTkAgg(fig, master=self.stats_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
