import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(layout="wide")
st.title("Analyse d’accordabilité C(V)")

# ============================================================
# Upload multiple fichiers
# ============================================================
uploaded_files = st.file_uploader(
    "Importer les fichiers CSV (séparateur tabulation)",
    type=["csv", "txt"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Veuillez importer un ou plusieurs fichiers de mesure.")
    st.stop()

all_curves = []
frequencies = []

# ============================================================
# Lecture & contrôles
# ============================================================
for file in uploaded_files:
    df = pd.read_csv(
        file,
        sep="\t",
        header=None,
        skiprows=0,
        engine="python"
    )

    if df.shape[1] < 4:
        st.error(f"{file.name} : nombre de colonnes insuffisant")
        st.stop()

    df = df.iloc[:, :4]
    df.columns = ["Freq_Hz", "DCB_V", "Cp_F", "Rp_Ohm"]

    # Vérification variation fréquence interne
    if df["Freq_Hz"].nunique() != 1:
        st.error("⚠️ Variation de fréquence détectée dans un fichier → condition anormale")
        st.stop()

    frequencies.append(df["Freq_Hz"].iloc[0])
    all_curves.append(df)

# ============================================================
# Vérification fréquence globale
# ============================================================
unique_freqs = np.unique(frequencies)

if len(unique_freqs) > 1:
    st.error("⚠️ Mesures à différentes fréquences entre fichiers")
else:
    st.success(f"Fréquence de mesure : **{unique_freqs[0]:.3e} Hz**")

# ============================================================
# Calcul accordabilité
# ============================================================
all_tuning = []

fig1, ax1 = plt.subplots()

for df, file in zip(all_curves, uploaded_files):

    df = df.sort_values("DCB_V")

    # Capacité en pF
    df["Cp_pF"] = df["Cp_F"] * 1e12

    # C0 à 0V
    if 0 not in df["DCB_V"].values:
        st.error(f"{file.name} : pas de point à 0V")
        st.stop()

    C0 = df.loc[df["DCB_V"] == 0, "Cp_pF"].iloc[0]

    df["Tune_pct"] = (C0 - df["Cp_pF"]) / C0 * 100

    all_tuning.append(df[["DCB_V", "Tune_pct"]])

    ax1.plot(df["DCB_V"], df["Tune_pct"], marker="o", label=file.name)

ax1.set_xlabel("Tension (V)")
ax1.set_ylabel("Accordabilité (%)")
ax1.grid(True)
ax1.legend()

# ============================================================
# Accordabilité par Volt
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

fig2, ax2 = plt.subplots()
ax2.errorbar(
    target_voltages,
    mean_tune_perV,
    yerr=std_tune_perV,
    marker="o",
    capsize=5
)
ax2.set_xlabel("Tension (V)")
ax2.set_ylabel("Accordabilité par Volt (%/V)")
ax2.grid(True)

# ============================================================
# Onglets
# ============================================================
tab1, tab2 = st.tabs(["📈 Accordabilité", "⚡ Accordabilité par Volt"])

with tab1:
    st.pyplot(fig1)

with tab2:
    st.pyplot(fig2)
