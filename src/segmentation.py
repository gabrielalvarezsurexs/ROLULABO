"""Problema 3. Segmentacion de clientes.

Pregunta analitica
    Existen grupos de clientes con comportamiento de compra y rentabilidad
    distintos que justifiquen politicas comerciales diferenciadas?

Tecnica. K-Means sobre variables RFM mas rentabilidad y descuento promedio.

    recency       dias desde la ultima compra al 2017-12-31
    frequency     numero de pedidos (log)
    monetary      ventas totales (log)
    margin        utilidad / ventas del cliente
    avg_discount  descuento promedio recibido

Las variables se estandarizan. El numero de grupos se elige con silueta,
Davies-Bouldin y codo, y la estabilidad se valida con ARI entre semillas y
con remuestreo bootstrap.
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from config import K_RANGE, METRICS, MODELS, PROCESSED, SEED
import viz

FEATURES = ["recency", "log_frequency", "log_monetary", "margin", "avg_discount"]


def load() -> pd.DataFrame:
    c = pd.read_csv(PROCESSED / "customers.csv")
    c["log_frequency"] = np.log1p(c["frequency"])
    c["log_monetary"] = np.log1p(c["monetary"])
    # Margen recortado para que pocos clientes extremos no dominen la distancia.
    c["margin"] = c["margin"].clip(c["margin"].quantile(0.01), c["margin"].quantile(0.99))
    return c


def choose_k(X) -> list[dict]:
    rows = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(X)
        rows.append({"k": k, "inercia": float(km.inertia_),
                     "silueta": float(silhouette_score(X, km.labels_)),
                     "davies_bouldin": float(davies_bouldin_score(X, km.labels_))})
    return rows


def stability(X, k: int, ref_labels) -> dict:
    seeds = [adjusted_rand_score(ref_labels, KMeans(n_clusters=k, n_init=20, random_state=s).fit(X).labels_)
             for s in range(20)]
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(50):
        idx = rng.choice(len(X), len(X), replace=True)
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(X[idx])
        boots.append(adjusted_rand_score(ref_labels, km.predict(X)))
    return {"ari_semillas_media": float(np.mean(seeds)), "ari_semillas_min": float(np.min(seeds)),
            "ari_bootstrap_media": float(np.mean(boots)), "ari_bootstrap_p05": float(np.percentile(boots, 5))}


def name_clusters(prof: pd.DataFrame) -> dict:
    """Asigna nombres de negocio a partir de los perfiles, con reglas
    explicitas para que el nombre no dependa del orden de las etiquetas."""
    names = {}
    remaining = set(prof.index)
    # El grupo con menor margen es el que destruye valor.
    worst = prof.loc[list(remaining), "margin"].idxmin()
    names[worst] = "Cazadores de descuento"
    remaining.discard(worst)
    # El de mayor recencia (mas dias sin comprar) es el inactivo.
    if remaining:
        inactive = prof.loc[list(remaining), "recency"].idxmax()
        names[inactive] = "Inactivos"
        remaining.discard(inactive)
    # El de mayor monto es el de alto valor.
    if remaining:
        top = prof.loc[list(remaining), "monetary"].idxmax()
        names[top] = "Alto valor rentable"
        remaining.discard(top)
    for i, c in enumerate(sorted(remaining)):
        names[c] = "Compradores ocasionales" if i == 0 else f"Grupo {c}"
    return names


def figure(c: pd.DataFrame, X, labels, names):
    import matplotlib.pyplot as plt
    pcs = PCA(n_components=2, random_state=SEED).fit_transform(X)
    markers = ["o", "s", "^", "D", "v", "P"]
    shades = [viz.BLACK, viz.DARK, viz.MID, viz.LIGHT, "#606060", "#b0b0b0"]
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    for i, k in enumerate(sorted(np.unique(labels))):
        m = labels == k
        ax.scatter(pcs[m, 0], pcs[m, 1], s=12, marker=markers[i], facecolor=shades[i],
                   edgecolor=viz.BLACK, lw=0.3, label=names[k], alpha=0.9)
    ax.set_xlabel("Componente principal 1")
    ax.set_ylabel("Componente principal 2")
    ax.legend(fontsize=7, loc="best")
    viz.save(fig, "f5_clusters_pca")


def run() -> dict:
    c = load()
    scaler = StandardScaler()
    X = scaler.fit_transform(c[FEATURES])
    ks = choose_k(X)

    # Regla de eleccion. Entre k = 3 y 6 (rango accionable para marketing)
    # se toma el menor k cuyo Davies-Bouldin queda a menos de 1% del minimo
    # del rango. Es un criterio de parsimonia, el codo de la inercia apunta
    # al mismo valor y la silueta se reporta como evidencia de que la
    # separacion entre grupos es moderada.
    candidates = [r for r in ks if 3 <= r["k"] <= 6]
    db_min = min(r["davies_bouldin"] for r in candidates)
    k = min(r["k"] for r in candidates if r["davies_bouldin"] <= db_min * 1.01)
    km = KMeans(n_clusters=k, n_init=50, random_state=SEED).fit(X)
    # Etiquetas ordenadas por ventas promedio para que sean deterministas.
    order = c.assign(l=km.labels_).groupby("l")["monetary"].mean().sort_values(ascending=False).index
    remap = {old: new for new, old in enumerate(order)}
    labels = np.array([remap[l] for l in km.labels_])
    c["cluster"] = labels

    prof = c.groupby("cluster").agg(
        clientes=("customer_id", "size"), recency=("recency", "mean"), frequency=("frequency", "mean"),
        monetary=("monetary", "mean"), profit=("profit", "mean"), margin=("margin", "mean"),
        avg_discount=("avg_discount", "mean"), loss_line_share=("loss_line_share", "mean"),
        late_rate=("late_rate", "mean"))
    names = name_clusters(prof)
    c["cluster_name"] = c["cluster"].map(names)
    prof["nombre"] = prof.index.map(names)
    tot_s, tot_p = c["monetary"].sum(), c["profit"].sum()
    share = c.groupby("cluster").agg(ventas=("monetary", "sum"), utilidad=("profit", "sum"),
                                     perdidas=("loss_amount", "sum"))
    prof["ventas_pct"] = share["ventas"] / tot_s
    prof["utilidad_pct"] = share["utilidad"] / tot_p
    prof["perdidas_pct"] = share["perdidas"] / c["loss_amount"].sum()
    prof["clientes_pct"] = prof["clientes"] / len(c)

    seg_mix = pd.crosstab(c["cluster_name"], c["segment"], normalize="index")

    stab_alt = {kk: stability(X, kk, KMeans(n_clusters=kk, n_init=50, random_state=SEED).fit(X).labels_)
                for kk in (3, 5)}
    out = {
        "estabilidad_alternativas": stab_alt,
        "features": FEATURES,
        "seleccion_k": ks,
        "k_elegido": int(k),
        "silueta_k": float(silhouette_score(X, labels)),
        "estabilidad": stability(X, k, labels),
        "perfiles": prof.reset_index().to_dict(orient="records"),
        "mezcla_segmento": seg_mix.round(3).to_dict(orient="index"),
        "centroides_escalados": pd.DataFrame(km.cluster_centers_, columns=FEATURES)
            .rename(index=remap).sort_index().round(3).to_dict(orient="index"),
    }
    c.to_csv(PROCESSED / "customers_clustered.csv", index=False)
    joblib.dump({"scaler": scaler, "kmeans": km, "remap": remap, "names": names, "features": FEATURES},
                MODELS / "segmentation.joblib")
    figure(c, X, labels, names)
    with open(METRICS / "segmentation.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=float)
    return out


if __name__ == "__main__":
    r = run()
    for row in r["seleccion_k"]:
        print(row)
    print("k =", r["k_elegido"], r["estabilidad"])
    pd.set_option("display.width", 250)
    print(pd.DataFrame(r["perfiles"]).round(3))
    print(r["mezcla_segmento"])
