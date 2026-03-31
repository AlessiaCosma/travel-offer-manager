import matplotlib.pyplot as plt


class StatisticaCalatorii:
    def __init__(self, df):
        self.df = df.copy()

    def afiseaza_grafice(self):
        if self.df.empty:
            return

        plt.figure(figsize=(8, 5))
        self.df["tip_oferta"].value_counts().plot(kind="bar")
        plt.title("Numărul ofertelor pe tip ofertă")
        plt.xlabel("Tip ofertă")
        plt.ylabel("Număr oferte")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.show()

        plt.figure(figsize=(8, 5))
        self.df["categorie"].value_counts().plot(kind="bar")
        plt.title("Numărul ofertelor pe categorie")
        plt.xlabel("Categorie")
        plt.ylabel("Număr oferte")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.show()

        plt.figure(figsize=(8, 5))
        self.df.dropna(subset=["pret_min"]).groupby("categorie")["pret_min"].mean().sort_values().plot(kind="bar")
        plt.title("Preț minim mediu pe categorie (EUR)")
        plt.xlabel("Categorie")
        plt.ylabel("Preț minim mediu (EUR)")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.show()

        plt.figure(figsize=(9, 5))
        self.df.dropna(subset=["oras_destinatie", "pret_min"]).groupby("oras_destinatie")["pret_min"].mean().sort_values().head(10).plot(kind="bar")
        plt.title("Top destinații după preț minim mediu (EUR)")
        plt.xlabel("Oraș destinație")
        plt.ylabel("Preț minim mediu (EUR)")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.show()
