import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

# ============================================================
# CONFIG GÉNÉRALE
# ============================================================
st.set_page_config(layout="wide")
st.title("Analyse d’accordabilité C(V)")

TOL_FREQ_REL = 1e-3   # 0.1 % tolérance fréquence

# Taille FIXE des figures (ne dépasse jamais la page)
FIG_W = 8.0   # pouces
FIG_H = 4.5

# ============================================================
# SIDEBAR – ZOOM VISUEL
# ============================================================
st.sidebar.header("Affichage")

zoom = st.sidebar.slider(
    "Zoom visuel (lignes / marqueurs)",
    min_value=0.5,
    max_value=2.0,
    value=1.0,
    step=0.1
)

LINE_W = 2.0 * zoom
MARKER_S = 6.0 * zoom

# ============================================================
# Upload fichiers
# ============================================================
uploaded_files = st.file_uploader(
    "Importer les fichiers CSV Agilent (séparateur tabulation)",
    type=["csv", "txt"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Veuillez importer un ou plusieurs fichiers de mesure.")
    st.stop()

all_curves = []
frequencies = []

# ============================================================
# Lecture & contrôles fichiers
# ============================================================
for file in uploaded_files:

    try:
        df = pd.read_csv(
            file,
            sep="\t",
            comment="!",
            engine="python"
        )
    except Exception as e:
        st.error(f"Erreur lecture {file.name} : {e}")
        st.stop()

    if df.shape[1] < 4:
        st.error(f"{file.name} : fichier invalide (moins de 4 colonnes)")
        st.stop()

    df = df.iloc[:, :4]
    df.columns = ["Freq_Hz", "DCB_V", "Cp_F", "Rp_Ohm"]

    try:
        df = df.astype(float)
    except Exception:
        st.error(f"{file.name} : conversion numérique impossible")
        st.stop()

    # ---- Contrôle fréquence interne ----
    freq_vals = df["Freq_Hz"].values
    f_min = freq_vals.min()
    f_max = freq_vals.max()

    if (f_max - f_min) / f_min > TOL_FREQ_REL:
        st.error(
            f"⚠️ Variation de fréquence détectée dans {file.name} "
            f"({f_min:.3e} → {f_max:.3e} Hz)"
        )
        st.stop()

    frequencies.append(freq_vals.mean())
    all_curves.append((df, file.name))

# ============================================================
# Vérification fréquence globale
# ============================================================
freqs = np.array(frequencies)
f_ref = freqs.mean()

if np.max(np.abs(freqs - f_ref) / f_ref) > TOL_FREQ_REL:
    st.error("⚠️ Mesures à différentes fréquences entre fichiers")
else:
    st.success(f"Fréquence de mesure : **{f_ref:.3e} Hz**")

# ============================================================
# CALCUL ACCORDABILITÉ
# ============================================================
all_tuning = []

fig1, ax1 = plt.subplots(figsize=(FIG_W, FIG_H))

for df, fname in all_curves:

    df = df.sort_values("DCB_V")
    df["Cp_pF"] = df["Cp_F"] * 1e12

    if 0 not in df["DCB_V"].values:
        st.error(f"{fname} : pas de point à 0 V")
        st.stop()

    C0 = df.loc[df["DCB_V"] == 0, "Cp_pF"].iloc[0]
    df["Tune_pct"] = (C0 - df["Cp_pF"]) / C0 * 100

    all_tuning.append(df[["DCB_V", "Tune_pct"]])

    ax1.plot(
        df["DCB_V"],
        df["Tune_pct"],
        marker="o",
        linewidth=LINE_W,
        markersize=MARKER_S,
        label=fname
    )

ax1.set_xlabel("Tension DC (V)")
ax1.set_ylabel("Accordabilité (%)")
ax1.grid(True)
ax1.legend()

# ============================================================
# ACCORDABILITÉ PAR VOLT
# ============================================================
target_voltages = np.arange(1, 25)
mean_tune_perV = []
std_tune_perV = []

for V in target_voltages:
    vals = []
    for df in all_tuning:
        idx = (df["DCB_V"] - V).abs().idxmin()
        vals.append(abs(df.loc[idx, "Tune_pct"]) / V)

    mean_tune_perV.append(np.mean(vals))
    std_tune_perV.append(np.std(vals))

fig2, ax2 = plt.subplots(figsize=(FIG_W, FIG_H))

ax2.errorbar(
    target_voltages,
    mean_tune_perV,
    yerr=std_tune_perV,
    marker="o",
    linewidth=LINE_W,
    markersize=MARKER_S,
    capsize=5
)

ax2.set_xlabel("Tension DC (V)")
ax2.set_ylabel("Accordabilité par Volt (%/V)")
ax2.grid(True)

# ============================================================
# INTERFACE ONGLET
# ============================================================
tab1, tab2 = st.tabs(
    ["📈 Accordabilité vs Tension", "⚡ Accordabilité par Volt"]
)

with tab1:
    st.pyplot(fig1, use_container_width=True)

with tab2:
    st.pyplot(fig2, use_container_width=True)
