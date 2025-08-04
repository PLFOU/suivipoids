import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime
import sqlite3
import os

# --- Sécurité via mot de passe ---
PASSWORD = os.getenv("APP_PASSWORD") or "changeme"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 Accès sécurisé")
    password = st.text_input("Mot de passe", type="password")
    if password == PASSWORD:
        st.session_state["authenticated"] = True
        st.success("Accès autorisé")
        st.experimental_rerun()
    elif password:
        st.error("Mot de passe incorrect")
    st.stop()

# --- Connexion base SQLite ---
DB_FILE = "suivi.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS mesures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            poids REAL,
            ventre REAL,
            poitrine REAL
        )
    """)
    conn.commit()
    conn.close()

def insert_mesure(date, poids, ventre, poitrine):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO mesures (date, poids, ventre, poitrine) VALUES (?, ?, ?, ?)",
              (date.strftime("%Y-%m-%d"), poids, ventre, poitrine))
    conn.commit()
    conn.close()

def get_mesures():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM mesures ORDER BY date", conn, parse_dates=["date"])
    conn.close()
    return df

# --- Initialisation DB ---
init_db()

# --- Formulaire d’entrée ---
st.title("Suivi poids & mensurations")
with st.form("ajout_mesure"):
    date = st.date_input("Date", datetime.today())
    poids = st.number_input("Poids (kg)", 30.0, 100.0, step=0.1)
    ventre = st.number_input("Tour de ventre (cm)", 50.0, 120.0, step=0.1)
    poitrine = st.number_input("Tour de poitrine (cm)", 50.0, 120.0, step=0.1)
    if st.form_submit_button("Ajouter"):
        insert_mesure(date, poids, ventre, poitrine)
        st.success("Mesure ajoutée avec succès ✅")

# --- Affichage des graphiques ---
df = get_mesures()
if not df.empty:
    st.subheader("📈 Évolution")
    for col in ["poids", "ventre", "poitrine"]:
        st.line_chart(df.set_index("date")[col])

    st.subheader("📊 Moyenne hebdo")
    df["week"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
    weekly_mean = df.groupby("week")[["poids", "ventre", "poitrine"]].mean()
    st.line_chart(weekly_mean)

    st.subheader("📉 Moyenne glissante (7 jours)")
    df_rolling = df.set_index("date").rolling("7D").mean()
    st.line_chart(df_rolling[["poids", "ventre", "poitrine"]])

    st.subheader("🔮 Prévision du poids (30 jours)")
    df['timestamp'] = df['date'].map(datetime.toordinal)
    X = df[['timestamp']]
    y = df['poids']
    model = LinearRegression().fit(X, y)

    future_dates = pd.date_range(df["date"].max(), periods=30)
    future_X = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)
    y_pred = model.predict(future_X)

    pred_df = pd.DataFrame({"date": future_dates, "poids_prevu": y_pred})
    chart_df = pd.concat([df[["date", "poids"]].rename(columns={"poids": "poids_prevu"}), pred_df])
    st.line_chart(chart_df.set_index("date"))
