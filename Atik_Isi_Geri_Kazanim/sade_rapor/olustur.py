# -*- coding: utf-8 -*-
"""14 MW gemi dizel motoru için R245fa ORC tasarım raporu (sade sürüm) -> RAPOR_ORC.pdf

Çalıştırma: python3 olustur.py   (CoolProp, matplotlib, Node.js + playwright gerekir)
"""
import math
import os
import subprocess

import CoolProp.CoolProp as CP
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

D = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "savefig.dpi": 200,
                     "savefig.bbox": "tight", "axes.spines.top": False, "axes.spines.right": False})
LAC, TUR, KIR, YES = "#1f3b57", "#d9822b", "#b03a2e", "#3b8b4b"

# ---------------------------------------------------------------- hesaplar
F = "R245fa"
T0 = 298.15
MG, CPG, TG_IN, TG_OUT = 25.0, 1.05e3, 320 + 273.15, 140 + 273.15   # egzoz (tasarım kabulü)
PH, TK, SH, ETA_T, ETA_P, U = 19e5, 40 + 273.15, 10.0, 0.80, 0.75, 50.0
MOTOR = 14e6

PL = CP.PropsSI("P", "T", TK, "Q", 0, F)
h1 = CP.PropsSI("H", "P", PL, "Q", 0, F)
s1 = CP.PropsSI("S", "P", PL, "Q", 0, F)
h2 = h1 + (CP.PropsSI("H", "P", PH, "S", s1, F) - h1) / ETA_P
T2 = CP.PropsSI("T", "P", PH, "H", h2, F)
TSAT = CP.PropsSI("T", "P", PH, "Q", 0, F)
HL = CP.PropsSI("H", "P", PH, "Q", 0, F)
T3 = TSAT + SH
h3 = CP.PropsSI("H", "P", PH, "T", T3, F)
s3 = CP.PropsSI("S", "P", PH, "T", T3, F)
h4 = h3 - ETA_T * (h3 - CP.PropsSI("H", "P", PL, "S", s3, F))
T4 = CP.PropsSI("T", "P", PL, "H", h4, F)
C = MG * CPG
Q = C * (TG_IN - TG_OUT)
M = Q / (h3 - h2)
TB = TG_OUT + M * (HL - h2) / C           # egzozun kabarcık noktası hizasındaki sıcaklığı
Q1, Q2 = M * (HL - h2), M * (h3 - HL)


def lmtd(a, b):
    return (a - b) / math.log(a / b)


L1 = lmtd(TB - TSAT, TG_OUT - T2)
L2 = lmtd(TG_IN - T3, TB - TSAT)
A1, A2 = Q1 / (U * L1), Q2 / (U * L2)
WT, WP = M * (h3 - h4), M * (h2 - h1)
WN = WT - WP
EX_HEX = C * ((TG_IN - TG_OUT) - T0 * math.log(TG_IN / TG_OUT))
R = dict(PL=PL / 1e5, TSAT=TSAT - 273.15, T2=T2 - 273.15, T3=T3 - 273.15, T4=T4 - 273.15,
         h1=h1 / 1e3, h2=h2 / 1e3, h3=h3 / 1e3, h4=h4 / 1e3, M=M, Q=Q / 1e3, TB=TB - 273.15,
         Q1=Q1 / 1e3, Q2=Q2 / 1e3, L1=L1, L2=L2, A1=A1, A2=A2, A=A1 + A2, WT=WT / 1e3, WP=WP / 1e3,
         WN=WN / 1e3, ETA=100 * WN / Q, QK=(Q - WN) / 1e3, EX=EX_HEX / 1e3, ETA2=100 * WN / EX_HEX,
         KAZ=100 * WN / MOTOR, PINCH=TB - TSAT)


def n(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- şekiller
def sekil_akis():
    adim = ["Sınır koşulları: motor ve egzoz verileri", "İş akışkanının seçimi (R245fa)",
            "1-B termodinamik çevrim hesabı (CoolProp)", "Evaporatör boyutlandırma (bölgesel LMTD)",
            "Ters basınç kontrolü (sonraki adım: CFD)"]
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ax.set_axis_off()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, len(adim))
    for i, t in enumerate(adim):
        y = len(adim) - 1 - i + 0.15
        ax.add_patch(plt.Rectangle((1, y), 8, 0.62, fc="#e8eef4" if i < 4 else "#fbeee0", ec=LAC, lw=1.1))
        ax.add_patch(plt.Rectangle((1, y), 1.3, 0.62, fc=LAC, ec=LAC))
        ax.text(1.65, y + 0.31, f"ADIM {i + 1}", color="w", ha="center", va="center", fontsize=8, weight="bold")
        ax.text(2.55, y + 0.31, t, va="center", fontsize=9)
        if i < len(adim) - 1:
            ax.annotate("", xy=(5, y - 0.2), xytext=(5, y), arrowprops=dict(arrowstyle="-|>", color=LAC))
    plt.savefig(os.path.join(D, "s1_akis.png"))
    plt.close()


def sekil_sema():
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.set_axis_off()
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)

    def kutu(x, y, w, h, t, r):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=r, ec="k", lw=1))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8)

    def ok(p, r, t=None, tx=None):
        xs, ys = zip(*p)
        ax.plot(xs[:-1] + (xs[-1],), ys, color=r, lw=1.6)
        ax.annotate("", xy=p[-1], xytext=p[-2], arrowprops=dict(arrowstyle="-|>", color=r, lw=1.6))
        if t:
            ax.text(*tx, t, fontsize=7.5, color=r)

    kutu(0.2, 3.6, 2.2, 1.6, "Ana motor\n14 MW", "#e8eef4")
    kutu(4.0, 3.6, 3.0, 1.6, "Evaporatör\nön ısıtıcı +\nbuharlaştırıcı +\nkızdırıcı", "#f6e3cf")
    kutu(8.8, 3.7, 2.4, 1.4, "Türbin + jeneratör", "#dcefd9")
    kutu(8.8, 0.5, 2.4, 1.4, "Kondenser\n(deniz suyu)", "#dde7f5")
    kutu(4.2, 0.5, 2.6, 1.4, "Pompa", "#dde7f5")
    ok([(2.4, 4.4), (4.0, 4.4)], KIR, "Egzoz\n320 °C\n25 kg/s", (2.55, 4.55))
    ok([(4.5, 3.6), (4.5, 2.9), (3.0, 2.9), (3.0, 2.2)], KIR)
    ax.text(0.35, 2.45, f"Bacaya {n(140, 0)} °C", fontsize=7.5, color=KIR)
    ok([(7.0, 4.6), (8.8, 4.6)], LAC, f"{n(R['T3'])} °C\n19 bar", (7.15, 4.75))
    ok([(10.0, 3.7), (10.0, 1.9)], LAC, f"{n(R['T4'])} °C, {n(R['PL'], 2)} bar", (10.1, 2.7))
    ok([(8.8, 1.2), (6.8, 1.2)], LAC, "sıvı 40 °C\n2,51 bar", (7.1, 1.35))
    ok([(6.2, 1.9), (6.2, 3.6)], LAC, "basınçlı sıvı", (6.3, 2.6))
    ok([(11.9, 0.7), (11.2, 0.7)], "#2471a3")
    ok([(11.2, 1.6), (11.9, 1.6)], "#2471a3")
    ax.text(10.95, 0.25, "Deniz suyu", fontsize=7.5, color="#2471a3")
    ax.text(11.3, 4.4, f"Ẇnet ≈ {n(R['WN'], 0)} kW", fontsize=8, weight="bold")
    plt.savefig(os.path.join(D, "s2_sema.png"))
    plt.close()


def sekil_ts_tq():
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    T = np.linspace(260, CP.PropsSI("Tcrit", F) - 0.05, 120)
    ax[0].plot([CP.PropsSI("S", "T", t, "Q", 0, F) / 1e3 for t in T], T - 273.15, "k", lw=0.9)
    ax[0].plot([CP.PropsSI("S", "T", t, "Q", 1, F) / 1e3 for t in T], T - 273.15, "k", lw=0.9, label="Doyma eğrisi")
    yol = [(CP.PropsSI("S", "P", PH, "H", h, F), CP.PropsSI("T", "P", PH, "H", h, F)) for h in np.linspace(h2, h3, 60)]
    yol += [(CP.PropsSI("S", "P", PL, "H", h4, F), T4)]
    yol += [(CP.PropsSI("S", "P", PL, "H", h, F), CP.PropsSI("T", "P", PL, "H", h, F)) for h in np.linspace(h4, h1, 40)]
    yol += [(CP.PropsSI("S", "P", PH, "H", h2, F), T2)]
    s, t = np.array(yol).T
    ax[0].plot(s / 1e3, t - 273.15, color=LAC, lw=2, label="R245fa ORC")
    for k, h, p in (("1", h1, PL), ("2", h2, PH), ("3", h3, PH), ("4", h4, PL)):
        ax[0].plot(CP.PropsSI("S", "P", p, "H", h, F) / 1e3, CP.PropsSI("T", "P", p, "H", h, F) - 273.15, "o", color=KIR)
        ax[0].annotate(k, (CP.PropsSI("S", "P", p, "H", h, F) / 1e3, CP.PropsSI("T", "P", p, "H", h, F) - 273.15),
                       textcoords="offset points", xytext=(5, 3))
    ax[0].set_xlabel("s [kJ/kg·K]")
    ax[0].set_ylabel("T [°C]")
    ax[0].set_title("(a) T–s diyagramı", fontsize=9)
    ax[0].legend(fontsize=7.5, loc="upper left")
    q = np.array([0, Q1, Q1 + Q2]) / 1e3
    ax[1].plot(q, [140, R["TB"], 320], "o-", color=KIR, label="Egzoz gazı")
    ax[1].plot([0, Q1 / 1e3, Q1 / 1e3 + M * (CP.PropsSI("H", "P", PH, "Q", 1, F) - HL) / 1e3, q[-1]],
               [R["T2"], R["TSAT"], R["TSAT"], R["T3"]], "s-", color=LAC, label="R245fa")
    ax[1].annotate(f"pinch ≈ {n(R['PINCH'], 0)} K", xy=(Q1 / 1e3, (R["TB"] + R["TSAT"]) / 2), xytext=(Q1 / 1e3 + 300, 60),
                   arrowprops=dict(arrowstyle="->"), fontsize=8)
    ax[1].set_xlabel("Aktarılan ısı [kW]")
    ax[1].set_ylabel("T [°C]")
    ax[1].set_title("(b) Evaporatör T–Q diyagramı", fontsize=9)
    ax[1].legend(fontsize=7.5)
    for a in ax:
        a.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(D, "s3_ts_tq.png"))
    plt.close()


# ---------------------------------------------------------------- HTML
def html_metin():
    r = {k: n(v, 1) for k, v in R.items()}
    r.update(PL=n(R["PL"], 2), h1=n(R["h1"]), M=n(R["M"], 2), A=n(R["A"], 0), A1=n(R["A1"], 0), A2=n(R["A2"], 0),
             Q=n(R["Q"], 0), WN=n(R["WN"], 0), KAZ=n(R["KAZ"], 1))
    return open(os.path.join(D, "sablon.html"), encoding="utf-8").read().format(**r)


def pdf():
    html = os.path.join(D, "rapor.html")
    open(html, "w", encoding="utf-8").write(html_metin())
    js = os.path.join(D, ".bas.js")
    open(js, "w").write(r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + process.argv[2], { waitUntil: 'networkidle' });
  await p.pdf({ path: process.argv[3], format: 'A4', printBackground: true, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="width:100%;text-align:center;font-family:Liberation Serif,serif;font-size:9px;"><span class="pageNumber"></span></div>',
    margin: { top: '18mm', bottom: '18mm', left: '19mm', right: '19mm' } });
  await b.close();
})();""")
    root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["node", js, html, os.path.join(os.path.dirname(D), "RAPOR_ORC_Tasarim.pdf")], check=True,
                   env={**os.environ, "NODE_PATH": root})
    os.remove(js)


if __name__ == "__main__":
    sekil_akis()
    sekil_sema()
    sekil_ts_tq()
    pdf()
    print({k: round(v, 2) for k, v in R.items()})
