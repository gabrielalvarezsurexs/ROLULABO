"""ETL de Rolulabo.

Extrae el CSV crudo, valida su calidad, limpia, deriva variables y guarda
tres tablas procesadas.

    lines.csv      una fila por linea de pedido
    orders.csv     una fila por pedido
    customers.csv  una fila por cliente (base para la segmentacion)

Ademas guarda reports/metrics/data_quality.json con el resultado de cada
validacion para que quede trazabilidad de las decisiones de limpieza.
"""
import json

import numpy as np
import pandas as pd

from config import METRICS, PROCESSED, RAW_CSV, REFERENCE_DATE, SLA_DAYS

EXPECTED_COLUMNS = [
    "Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode",
    "Customer ID", "Customer Name", "Segment", "Country", "City", "State",
    "Postal Code", "Region", "Product ID", "Category", "Sub-Category",
    "Product Name", "Sales", "Quantity", "Discount", "Profit",
]

RENAME = {
    "Row ID": "row_id", "Order ID": "order_id", "Order Date": "order_date",
    "Ship Date": "ship_date", "Ship Mode": "ship_mode",
    "Customer ID": "customer_id", "Customer Name": "customer_name",
    "Segment": "segment", "Country": "country", "City": "city",
    "State": "state", "Postal Code": "postal_code", "Region": "region",
    "Product ID": "product_id", "Category": "category",
    "Sub-Category": "sub_category", "Product Name": "product_name",
    "Sales": "sales", "Quantity": "quantity", "Discount": "discount",
    "Profit": "profit",
}


def extract() -> pd.DataFrame:
    # El archivo original viene en latin-1 (nombres con acentos).
    return pd.read_csv(RAW_CSV, encoding="latin-1")


def validate_and_clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    q = {}
    q["filas_crudas"] = int(len(raw))
    q["columnas_esperadas_ok"] = list(raw.columns) == EXPECTED_COLUMNS
    q["nulos_totales"] = int(raw.isna().sum().sum())

    df = raw.rename(columns=RENAME).copy()
    df["order_date"] = pd.to_datetime(df["order_date"], format="%m/%d/%Y")
    df["ship_date"] = pd.to_datetime(df["ship_date"], format="%m/%d/%Y")

    # Duplicados exactos ignorando el identificador de fila.
    dup_mask = df.drop(columns="row_id").duplicated(keep="first")
    q["duplicados_exactos_eliminados"] = int(dup_mask.sum())
    df = df[~dup_mask].copy()

    # Reglas de dominio.
    q["envio_antes_de_pedido"] = int((df["ship_date"] < df["order_date"]).sum())
    q["ventas_no_positivas"] = int((df["sales"] <= 0).sum())
    q["cantidad_no_positiva"] = int((df["quantity"] <= 0).sum())
    q["descuento_fuera_de_rango"] = int(((df["discount"] < 0) | (df["discount"] >= 1)).sum())
    q["paises"] = df["country"].unique().tolist()

    # Consistencia a nivel pedido. Un pedido debe tener una sola fecha,
    # modalidad de envio y cliente.
    per_order = df.groupby("order_id").agg(
        fechas=("order_date", "nunique"),
        modos=("ship_mode", "nunique"),
        clientes=("customer_id", "nunique"),
    )
    q["pedidos_inconsistentes"] = int((per_order.max(axis=1) > 1).sum())

    # Hallazgo de calidad. Algunos Product ID se reutilizan para dos
    # productos distintos, por eso la llave de producto es id + nombre.
    names_per_id = df.groupby("product_id")["product_name"].nunique()
    q["product_id_reutilizados"] = int((names_per_id > 1).sum())

    # Hallazgo de calidad. El descuento es unico por estado y subcategoria.
    disc_per_combo = df.groupby(["state", "sub_category"])["discount"].nunique()
    q["combinaciones_estado_subcategoria"] = int(len(disc_per_combo))
    q["combinaciones_con_un_solo_descuento"] = int((disc_per_combo == 1).sum())

    q["filas_limpias"] = int(len(df))
    q["periodo"] = [str(df["order_date"].min().date()), str(df["order_date"].max().date())]
    return df, q


def add_features(df: pd.DataFrame, q: dict) -> pd.DataFrame:
    df = df.copy()
    df["product_key"] = df["product_id"] + " | " + df["product_name"]
    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.month
    df["dow"] = df["order_date"].dt.dayofweek
    df["days_to_ship"] = (df["ship_date"] - df["order_date"]).dt.days

    # Precio de lista unitario antes del descuento.
    df["list_price"] = df["sales"] / df["quantity"] / (1 - df["discount"])
    # Costo unitario implicito. Utilidad = ventas - cantidad * costo.
    df["unit_cost"] = (df["sales"] - df["profit"]) / df["quantity"]
    df["cost_ratio"] = df["unit_cost"] / df["list_price"]
    # Descuento a partir del cual la linea pierde dinero.
    df["breakeven_discount"] = 1 - df["cost_ratio"]

    df["margin"] = df["profit"] / df["sales"]
    df["is_loss"] = (df["profit"] < 0).astype(int)

    # Validacion. El costo unitario debe ser constante por producto.
    cv = df.groupby("product_key")["unit_cost"].agg(lambda s: s.std(ddof=0) / s.mean())
    q["productos_costo_no_constante"] = int((cv > 1e-6).sum())

    # Validacion. La regla de equilibrio explica todas las perdidas.
    rule = (df["discount"] > df["breakeven_discount"] + 1e-9).astype(int)
    q["regla_equilibrio_exactitud"] = float((rule == df["is_loss"]).mean())
    return df


def build_orders(lines: pd.DataFrame) -> pd.DataFrame:
    orders = lines.groupby("order_id").agg(
        order_date=("order_date", "first"),
        ship_date=("ship_date", "first"),
        ship_mode=("ship_mode", "first"),
        customer_id=("customer_id", "first"),
        segment=("segment", "first"),
        region=("region", "first"),
        state=("state", "first"),
        n_lines=("row_id", "size"),
        sales=("sales", "sum"),
        profit=("profit", "sum"),
        avg_discount=("discount", "mean"),
        main_category=("category", lambda s: s.mode().iloc[0]),
    ).reset_index()
    orders["days_to_ship"] = (orders["ship_date"] - orders["order_date"]).dt.days
    orders["sla_days"] = orders["ship_mode"].map(SLA_DAYS)
    orders["is_late"] = (orders["days_to_ship"] > orders["sla_days"]).astype(int)
    orders["year"] = orders["order_date"].dt.year
    orders["month"] = orders["order_date"].dt.month
    orders["dow"] = orders["order_date"].dt.dayofweek
    orders["is_loss"] = (orders["profit"] < 0).astype(int)
    return orders


def build_customers(lines: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    ref = pd.Timestamp(REFERENCE_DATE)
    c = orders.groupby("customer_id").agg(
        segment=("segment", "first"),
        last_order=("order_date", "max"),
        first_order=("order_date", "min"),
        frequency=("order_id", "nunique"),
        monetary=("sales", "sum"),
        profit=("profit", "sum"),
        late_rate=("is_late", "mean"),
    )
    c["recency"] = (ref - c["last_order"]).dt.days
    c["tenure"] = (ref - c["first_order"]).dt.days
    line_stats = lines.groupby("customer_id").agg(
        avg_discount=("discount", "mean"),
        loss_line_share=("is_loss", "mean"),
        loss_amount=("profit", lambda s: -s[s < 0].sum()),
        n_lines=("row_id", "size"),
    )
    c = c.join(line_stats)
    c["margin"] = c["profit"] / c["monetary"]
    return c.reset_index()


def build_star_schema(lines: pd.DataFrame) -> dict:
    """Modelo estrella para la capa de BI (Power BI, Looker Studio o Tableau).

    Una tabla de hechos a nivel línea y cuatro dimensiones con llaves
    sustitutas. Se guarda en data/processed/bi/.
    """
    out = PROCESSED / "bi"
    out.mkdir(exist_ok=True)
    geo = lines[["country", "region", "state", "city", "postal_code"]].drop_duplicates().reset_index(drop=True)
    geo.insert(0, "geo_key", geo.index + 1)
    prod = lines[["product_key", "product_id", "product_name", "category", "sub_category", "list_price", "unit_cost"]] \
        .drop_duplicates("product_key").reset_index(drop=True)
    prod.insert(0, "producto_key", prod.index + 1)
    cli = lines[["customer_id", "customer_name", "segment"]].drop_duplicates("customer_id").reset_index(drop=True)
    cli.insert(0, "cliente_key", cli.index + 1)
    fechas = pd.date_range(lines["order_date"].min(), lines["ship_date"].max(), freq="D")
    fecha = pd.DataFrame({"fecha": fechas})
    fecha["fecha_key"] = fecha["fecha"].dt.strftime("%Y%m%d").astype(int)
    fecha["anio"], fecha["trimestre"], fecha["mes"] = fecha["fecha"].dt.year, fecha["fecha"].dt.quarter, fecha["fecha"].dt.month
    fecha["dia_semana"] = fecha["fecha"].dt.dayofweek

    f = lines.merge(geo, on=["country", "region", "state", "city", "postal_code"]) \
        .merge(prod[["producto_key", "product_key"]], on="product_key") \
        .merge(cli[["cliente_key", "customer_id"]], on="customer_id")
    f["fecha_pedido_key"] = f["order_date"].dt.strftime("%Y%m%d").astype(int)
    f["fecha_envio_key"] = f["ship_date"].dt.strftime("%Y%m%d").astype(int)
    fact = f[["row_id", "order_id", "fecha_pedido_key", "fecha_envio_key", "cliente_key", "producto_key", "geo_key",
              "ship_mode", "sales", "quantity", "discount", "profit", "breakeven_discount", "is_loss", "days_to_ship"]]
    for name, d in {"fact_lineas": fact, "dim_geografia": geo, "dim_producto": prod,
                    "dim_cliente": cli, "dim_fecha": fecha}.items():
        d.to_csv(out / f"{name}.csv", index=False)
    return {"fact_lineas": len(fact), "dim_geografia": len(geo), "dim_producto": len(prod),
            "dim_cliente": len(cli), "dim_fecha": len(fecha)}


def run() -> dict:
    raw = extract()
    df, q = validate_and_clean(raw)
    lines = add_features(df, q)
    orders = build_orders(lines)
    customers = build_customers(lines, orders)
    q["modelo_estrella"] = build_star_schema(lines)
    assert q["modelo_estrella"]["fact_lineas"] == len(lines), "la tabla de hechos perdió filas en los joins"

    lines.to_csv(PROCESSED / "lines.csv", index=False)
    orders.to_csv(PROCESSED / "orders.csv", index=False)
    customers.to_csv(PROCESSED / "customers.csv", index=False)

    q["pedidos"] = int(len(orders))
    q["clientes"] = int(len(customers))
    q["lineas_con_perdida_pct"] = float(lines["is_loss"].mean())
    q["pedidos_con_perdida_pct"] = float(orders["is_loss"].mean())
    q["ventas_totales"] = float(lines["sales"].sum())
    q["utilidad_total"] = float(lines["profit"].sum())
    q["monto_perdidas"] = float(-lines.loc[lines["profit"] < 0, "profit"].sum())

    with open(METRICS / "data_quality.json", "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)
    return q


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k}: {v}")
