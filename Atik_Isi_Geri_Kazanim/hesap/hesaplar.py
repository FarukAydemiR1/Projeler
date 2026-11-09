# -*- coding: utf-8 -*-
"""
İçten yanmalı motorlarda atık ısı geri kazanımı — rapor hesapları ve şekilleri.

Bu betik iki tür çıktı üretir ve bunları birbirinden ayırır:

  (L) LİTERATÜR VERİSİ: Yayınlardaki tablolarda verilen sayılar (ör. Mavridou vd.
      2010, Tablo 1, 2, 6a, 6b) değiştirilmeden bu dosyaya girilmiş ve yalnızca
      yeniden çizilmiştir. Her veri bloğunun üstünde kaynağı yazılıdır.

  (H) BU ÇALIŞMADA YAPILAN HESAPLAR: Literatür sınır koşullarını kullanan, fakat
      sonuçları literatürde yer almayan, yazarın kendi hesaplarıdır (ORC çevrim
      analizi, LMTD/UA kontrolü, TEG ve güç türbini kestirimleri). Akışkan
      özellikleri CoolProp (REFPROP benzeri Helmholtz denklemleri) ile alınmıştır.

Çalıştırma:  python3 hesaplar.py   ->  ../sekiller/*.png ve sonuclar.json
"""
import json
import math
import os

import CoolProp.CoolProp as CP
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

BURADA = os.path.dirname(os.path.abspath(__file__))
SEKIL = os.path.join(BURADA, "..", "sekiller")
os.makedirs(SEKIL, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})
RENK = ["#1f5f8b", "#d9822b", "#3b8b4b", "#a23b3b", "#6b4c9a", "#7a7a7a"]
T0 = 298.15          # ölü hal sıcaklığı [K]
P0 = 101325.0        # ölü hal basıncı [Pa]
SONUC = {}


def kaydet(ad, not_metni):
    fig = plt.gcf()
    fig.text(0.0, -0.02, not_metni, fontsize=7.5, color="#444444", ha="left", va="top", wrap=True)
    plt.savefig(os.path.join(SEKIL, ad))
    plt.close()


# =============================================================================
# (L) Mavridou vd. (2010) [Kaynak 5] — Tablo 1: motor çalışma matrisi
#     6 silindirli, 362 kW @1700 rpm ağır vasıta dizel motoru
# =============================================================================
MAV_T1 = [  # yük %, devir rpm, egzoz T [°C], HEX ısı yükü [kW], egzoz debisi [kg/s]
    (100, 1300, 503.5, 136.44, 0.490), (75, 1300, 459.3, 91.30, 0.395),
    (50, 1300, 394.2, 55.45, 0.306), (25, 1300, 363.1, 33.93, 0.205),
    (100, 1700, 483.7, 128.37, 0.512), (75, 1700, 423.3, 89.26, 0.441),
    (50, 1700, 353.6, 60.18, 0.368), (25, 1700, 334.5, 36.67, 0.246),
    (100, 2100, 435.2, 92.27, 0.439), (75, 2100, 382.4, 71.32, 0.410),
    (50, 2100, 317.6, 51.62, 0.352), (25, 2100, 291.0, 34.19, 0.269),
]

# (L) Mavridou vd. (2010) — Tablo 2: tasarım noktası (100 % yük, 1300 rpm)
MAV_T2 = {
    "Ön ısıtıcı":   dict(Q=31.41, Th1=318.02, Th2=261.2, Tc1=90.56, Tc2=239.2),
    "Buharlaştırıcı": dict(Q=85.27, Th1=469.2, Th2=318.02, Tc1=239.2, Tc2=239.2),
    "Kızdırıcı":    dict(Q=19.76, Th1=503.5, Th2=469.2, Tc1=239.2, Tc2=394.2),
}
MAV_MW, MAV_MG, MAV_P = 0.048, 0.49, 33e5   # su-buhar debisi, egzoz debisi, su basıncı

# (L) Mavridou vd. (2010) — Tablo 6a/6b: göreli büyüklükler (düz borulu gövde-boru = 1)
MAV_T6 = [  # ad, Vtot [m3], m/mo, Δp/Δpo (aralık verilenlerde orta değer + aralık)
    ("Gövde-boru\n(düz boru)", 0.200, 1.00, 1.00, None),
    ("Gövde-boru\n(sığ çukurcuklu)", 0.176, 0.88, 0.95, (0.8, 1.1)),
    ("Gövde-boru\n(derin çukurcuklu)", 0.178, 0.89, 0.95, (0.8, 1.1)),
    ("Gövde-boru\n(kanatlı boru)", 0.217, 0.49, 0.553, None),
    ("Plaka-kanat\n(düz kanat)", 0.0726, 0.59, 0.014, None),
    ("Plaka-kanat\n(10 ppi köpük)", 0.0775, 0.41, 0.161, None),
    ("Plaka-kanat\n(40 ppi köpük)", 0.0448, 0.27, 0.317, None),
]


# =============================================================================
# (H) Hesap 1 — Mavridou Tablo 2 verisinden LMTD, UA ve egzoz cp kontrolü
# =============================================================================
def lmtd_ters_akis(Th1, Th2, Tc1, Tc2):
    d1, d2 = Th1 - Tc2, Th2 - Tc1
    return d1 if abs(d1 - d2) < 1e-9 else (d1 - d2) / math.log(d1 / d2)


h1 = {}
for ad, d in MAV_T2.items():
    L = lmtd_ters_akis(d["Th1"], d["Th2"], d["Tc1"], d["Tc2"])
    cp_g = d["Q"] / (MAV_MG * (d["Th1"] - d["Th2"]))
    h1[ad] = dict(LMTD_K=round(L, 2), UA_kW_K=round(d["Q"] / L, 4), cp_egzoz_kJkgK=round(cp_g, 4))
# su-buhar tarafı enerji dengesi (CoolProp, IAPWS-95)
h_in = CP.PropsSI("H", "T", 90.56 + 273.15, "P", MAV_P, "Water")
h_l = CP.PropsSI("H", "P", MAV_P, "Q", 0, "Water")
h_v = CP.PropsSI("H", "P", MAV_P, "Q", 1, "Water")
h_out = CP.PropsSI("H", "T", 394.2 + 273.15, "P", MAV_P, "Water")
Tsat = CP.PropsSI("T", "P", MAV_P, "Q", 0, "Water") - 273.15
h1["su_tarafi"] = dict(
    Tsat_33bar_C=round(Tsat, 2),
    Q_onisitici_kW=round(MAV_MW * (h_l - h_in) / 1e3, 2),
    Q_buharlastirici_kW=round(MAV_MW * (h_v - h_l) / 1e3, 2),
    Q_kizdirici_kW=round(MAV_MW * (h_out - h_v) / 1e3, 2),
    Q_toplam_kW=round(MAV_MW * (h_out - h_in) / 1e3, 2),
    Q_toplam_Mavridou_kW=136.44,
)
SONUC["hesap1_lmtd_ua"] = h1

# =============================================================================
# (H) Hesap 2 — Basit (rejeneratörsüz) Rankine/ORC çevrim analizi
#     Isı kaynağı: Mavridou Tablo 1, 100 % yük / 1300 rpm egzozu (503.5 °C, 0.49 kg/s)
# =============================================================================
CP_G = float(np.mean([v["cp_egzoz_kJkgK"] for k, v in h1.items() if k != "su_tarafi"])) * 1e3
TG_IN, MG = 503.5 + 273.15, 0.49
ETA_T, ETA_P = 0.70, 0.60      # genleştirici / pompa izentropik verimi (varsayım; bkz. rapor Tablo 6)
T_KOND = 50 + 273.15           # yoğuşma sıcaklığı (araç radyatörü için tipik varsayım)
PINCH = 30.0                   # egzoz tarafı minimum sıcaklık farkı [K]
TG_MIN = 120 + 273.15          # egzoz çıkışı alt sınırı (asit yoğuşması/ters basınç) [K]


def egzoz_ekserjisi(T_in, T_out):
    """Mükemmel gaz, sabit cp kabulüyle egzoz akışının ekserji değişimi [W]."""
    return MG * CP_G * ((T_in - T_out) - T0 * math.log(T_in / T_out))


def cevrim(akiskan, T_buh_C, kizdirma_K, T_kond=None):
    T_K = T_KOND if T_kond is None else T_kond + 273.15
    """Basit Rankine: 1 pompa girişi (doymuş sıvı), 2 pompa çıkışı, 3 türbin girişi, 4 türbin çıkışı."""
    T_buh = T_buh_C + 273.15
    p_low = CP.PropsSI("P", "T", T_K, "Q", 0, akiskan)
    p_high = CP.PropsSI("P", "T", T_buh, "Q", 0, akiskan)
    h1_ = CP.PropsSI("H", "P", p_low, "Q", 0, akiskan)
    s1 = CP.PropsSI("S", "P", p_low, "Q", 0, akiskan)
    h2s = CP.PropsSI("H", "P", p_high, "S", s1, akiskan)
    h2 = h1_ + (h2s - h1_) / ETA_P
    T3 = T_buh + kizdirma_K
    h3 = CP.PropsSI("H", "P", p_high, "T", T3, akiskan) if kizdirma_K > 0 else CP.PropsSI("H", "P", p_high, "Q", 1, akiskan)
    s3 = CP.PropsSI("S", "P", p_high, "H", h3, akiskan)
    h4s = CP.PropsSI("H", "P", p_low, "S", s3, akiskan)
    h4 = h3 - ETA_T * (h3 - h4s)
    h_sl = CP.PropsSI("H", "P", p_high, "Q", 0, akiskan)
    # Akışkan debisi: (i) egzoz çıkışı >= TG_MIN, (ii) buharlaşma başlangıcında pinch >= PINCH
    m_a = MG * CP_G * (TG_IN - TG_MIN) / (h3 - h2)
    m_b = MG * CP_G * (TG_IN - (T_buh + PINCH)) / (h3 - h_sl)
    m = min(m_a, m_b)
    Q_in = m * (h3 - h2)
    Tg_out = TG_IN - Q_in / (MG * CP_G)
    W_t, W_p = m * (h3 - h4), m * (h2 - h1_)
    W_net = W_t - W_p
    Ex_in = egzoz_ekserjisi(TG_IN, T0)            # egzozun toplam (termal) ekserjisi
    Ex_hex = egzoz_ekserjisi(TG_IN, Tg_out)       # HEX'te egzozdan alınan ekserji
    s = {k: CP.PropsSI("S", "P", p, "H", h, akiskan) for k, p, h in
         (("1", p_low, h1_), ("2", p_high, h2), ("3", p_high, h3), ("4", p_low, h4))}
    # bileşen ekserji yıkımları (Gouy–Stodola), yoğuşturucuda ısı ölü hale atılıyor kabulü
    I_pompa = m * T0 * (s["2"] - s["1"])
    I_turb = m * T0 * (s["4"] - s["3"])
    I_hex = Ex_hex - m * ((h3 - h2) - T0 * (s["3"] - s["2"]))
    I_kond = m * ((h4 - h1_) - T0 * (s["4"] - s["1"]))
    T = {k: CP.PropsSI("T", "P", p, "H", h, akiskan) - 273.15 for k, p, h in
         (("1", p_low, h1_), ("2", p_high, h2), ("3", p_high, h3), ("4", p_low, h4))}
    return dict(
        akiskan=akiskan, T_buh_C=T_buh_C, kizdirma_K=kizdirma_K,
        p_yuksek_bar=p_high / 1e5, p_dusuk_bar=p_low / 1e5, m_kg_s=m, Q_in_kW=Q_in / 1e3,
        Tg_cikis_C=Tg_out - 273.15, W_turbin_kW=W_t / 1e3, W_pompa_kW=W_p / 1e3, W_net_kW=W_net / 1e3,
        eta_th=W_net / Q_in, eta_II_hex=W_net / Ex_hex, eta_II_toplam=W_net / Ex_in,
        Ex_egzoz_kW=Ex_in / 1e3, I_hex_kW=I_hex / 1e3, I_turbin_kW=I_turb / 1e3,
        I_pompa_kW=I_pompa / 1e3, I_kond_kW=I_kond / 1e3,
        Ex_atilan_egzoz_kW=(Ex_in - Ex_hex) / 1e3,
        x4_kuruluk=CP.PropsSI("Q", "P", p_low, "H", h4, akiskan),
        durumlar_T_C=T, durumlar_s=s,
        durumlar_h={"1": h1_, "2": h2, "3": h3, "4": h4}, p=(p_low, p_high),
    )


TASARIMLAR = [("R245fa", 140, 10), ("Ethanol", 200, 20), ("Toluene", 250, 10), ("Water", Tsat, 155.0)]
cevrimler = [cevrim(*t) for t in TASARIMLAR]
SONUC["hesap2_orc"] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items()
                        if k not in ("durumlar_s", "durumlar_h", "p")} for c in cevrimler]

# (H) Hesap 2b — yoğuşma sıcaklığı 90 °C (araç soğutma paketine daha gerçekçi) duyarlılığı
SONUC["hesap2b_Tkond90"] = [
    {k: round(v, 4) for k, v in cevrim(*t, T_kond=90).items() if k in ("W_net_kW", "eta_th", "eta_II_toplam", "p_dusuk_bar")}
    | {"akiskan": t[0]} for t in TASARIMLAR]

# (H) Hesap 3 — R245fa ve etanol için buharlaşma sıcaklığı duyarlılığı
duyar = {}
for ak, Tlist, sh in (("R245fa", np.arange(90, 151, 5), 10), ("Ethanol", np.arange(130, 231, 10), 20)):
    duyar[ak] = [(float(T), cevrim(ak, float(T), sh)) for T in Tlist]
SONUC["hesap3_duyarlilik"] = {ak: [(T, round(c["W_net_kW"], 3), round(c["eta_th"], 4), round(c["eta_II_toplam"], 4))
                                   for T, c in v] for ak, v in duyar.items()}

# (H) Hesap 4 — TEG modül verimi (Ioffe ifadesi) ve Kim vd. (2016) ile tutarlılık
def teg_verim(Th, Tc, ZT):
    return (Th - Tc) / Th * (math.sqrt(1 + ZT) - 1) / (math.sqrt(1 + ZT) + Tc / Th)


SONUC["hesap4_teg"] = {
    "eta_ZT1_Th250_Tc50": round(teg_verim(523.15, 323.15, 1.0), 4),
    "eta_ZT1_Th300_Tc80": round(teg_verim(573.15, 353.15, 1.0), 4),
    "Kim2016_isi_akisi_kW (119 W / 0.028)": round(0.119 / 0.028, 2),
}

# (H) Hesap 5 — Güç türbini (turbo-kompaund) kaba kestirimi, Mavridou Tablo 1 egzozu
def guc_turbini(T_in_C, m, PR, eta=0.70, gamma=1.34):
    return m * CP_G * (T_in_C + 273.15) * eta * (1 - PR ** (-(gamma - 1) / gamma)) / 1e3


PRs = np.linspace(1.05, 1.8, 40)
SONUC["hesap5_turbokompaund"] = {
    f"PR={pr}": round(guc_turbini(503.5, 0.49, pr), 2) for pr in (1.2, 1.4, 1.6)}

# =============================================================================
# ŞEKİLLER
# =============================================================================
# Şekil A — Atık ısı kaynaklarının sıcaklık aralıkları (Lion vd. 2017 [6], Bölüm 2.3)
kaynaklar = [("Egzoz gazı", 200, 600), ("EGR", 200, 750), ("Yağlama yağı", 80, 120),
             ("Soğutma suyu", 80, 100), ("Şarj havası soğutucu (CAC)", 50, 70)]
plt.figure(figsize=(7.5, 3.2))
for i, (ad, a, b) in enumerate(kaynaklar):
    plt.barh(i, b - a, left=a, color=RENK[0] if a >= 200 else RENK[1], height=0.55)
    plt.text(b + 8, i, f"{a}–{b} °C", va="center", fontsize=9)
plt.yticks(range(len(kaynaklar)), [k[0] for k in kaynaklar])
plt.xlabel("Sıcaklık [°C]")
plt.xlim(0, 850)
plt.title("Ağır vasıta dizel motorlarında atık ısı kaynaklarının sıcaklık aralıkları")
kaydet("sekil01_kaynak_sicakliklari.png",
       "Veri: Lion vd. (2017) [6], Bölüm 2.3 'Heat sources' metninden aktarılmıştır; grafik bu çalışmada çizilmiştir. "
       "Mavi: yüksek sıcaklık, turuncu: düşük sıcaklık kaynakları.")

# Şekil B — Mavridou Tablo 1: HEX ısı yükü ve egzoz sıcaklığı
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
yukler = [100, 75, 50, 25]
w = 0.26
for j, n in enumerate((1300, 1700, 2100)):
    satir = [r for r in MAV_T1 if r[1] == n]
    ax[0].bar(np.arange(4) + (j - 1) * w, [r[3] for r in satir], w, color=RENK[j], label=f"{n} rpm")
    ax[1].plot(yukler, [r[2] for r in satir], "o-", color=RENK[j], label=f"{n} rpm")
ax[0].set_xticks(range(4), [f"%{y}" for y in yukler])
ax[0].set_xlabel("Motor yükü")
ax[0].set_ylabel("Isı değiştiricide aktarılan ısı [kW]")
ax[0].legend()
ax[0].set_title("(a) Geri kazanılabilir egzoz ısısı")
ax[1].set_xlabel("Motor yükü [%]")
ax[1].set_ylabel("Egzoz gazı sıcaklığı [°C]")
ax[1].set_title("(b) Türbin sonrası egzoz sıcaklığı")
ax[1].legend()
kaydet("sekil02_mavridou_tablo1.png",
       "Veri: Mavridou vd. (2010) [5], Tablo 1 (362 kW, 6 silindirli ağır vasıta dizel motoru). Sayılar değiştirilmeden "
       "aktarılmış, grafik bu çalışmada çizilmiştir.")

# Şekil C — Mavridou Tablo 2: T–Q diyagramı (egzoz / su-buhar)
Qkum = np.cumsum([0, 31.41, 85.27, 19.76])
plt.figure(figsize=(7, 4.2))
plt.plot(Qkum, [261.2, 318.02, 469.2, 503.5], "o-", color=RENK[3], label="Egzoz gazı (0.49 kg/s)")
plt.plot(Qkum, [90.56, 239.2, 239.2, 394.2], "s-", color=RENK[0], label="Su–buhar (0.048 kg/s, 33 bar)")
for x, ad in zip((Qkum[0] + Qkum[1]) / 2 + np.array([0]), ["Ön ısıtıcı"]):
    pass
for xa, xb, ad in ((Qkum[0], Qkum[1], "Ön ısıtıcı"), (Qkum[1], Qkum[2], "Buharlaştırıcı"), (Qkum[2], Qkum[3], "Kızdırıcı")):
    plt.axvspan(xa, xb, alpha=0.06, color="k")
    plt.text((xa + xb) / 2, 40, ad, ha="center", fontsize=8.5)
plt.annotate("pinch ≈ 79 K", xy=(Qkum[1], 280), xytext=(Qkum[1] + 8, 170), arrowprops=dict(arrowstyle="->"), fontsize=8.5)
plt.xlabel("Kümülatif aktarılan ısı [kW]")
plt.ylabel("Sıcaklık [°C]")
plt.ylim(0, 560)
plt.legend(loc="upper left")
plt.title("Egzoz ısı değiştiricisi T–Q diyagramı (tasarım noktası %100 yük, 1300 rpm)")
kaydet("sekil05_TQ_mavridou.png",
       "Veri: Mavridou vd. (2010) [5], Tablo 2. Grafik ve pinch değeri (318.02 − 239.2 = 78.8 K) bu çalışmada "
       "türetilmiştir.")

# Şekil D — Mavridou Tablo 6: göreli hacim, kütle ve basınç kaybı
fig, ax1 = plt.subplots(figsize=(10, 4))
x = np.arange(len(MAV_T6))
ax1.bar(x - 0.2, [r[1] * 1000 for r in MAV_T6], 0.4, color=RENK[0], label="Toplam hacim [L]")
ax1.set_ylabel("Toplam hacim [L]")
ax2 = ax1.twinx()
ax2.bar(x + 0.2, [r[2] for r in MAV_T6], 0.4, color=RENK[1], label="Göreli kütle m/m₀")
ax2.plot(x, [r[3] for r in MAV_T6], "kD", label="Göreli basınç kaybı Δp/Δp₀")
for i, r in enumerate(MAV_T6):
    lab = f"{r[4][0]}–{r[4][1]}" if r[4] else f"{r[3]:.3g}"
    ax2.text(i, r[3] + 0.04, lab, ha="center", fontsize=7.5)
ax2.set_ylabel("Göreli kütle / göreli Δp [–]")
ax2.set_ylim(0, 1.25)
ax2.grid(False)
ax1.set_xticks(x, [r[0] for r in MAV_T6], fontsize=8)
h1_, l1 = ax1.get_legend_handles_labels()
h2_, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1_ + h2_, l1 + l2, loc="upper right", fontsize=8)
plt.title("Aynı ısı yükü (136.44 kW) için yedi egzoz ısı değiştiricisi tasarımının karşılaştırması")
kaydet("sekil06_mavridou_tablo6.png",
       "Veri: Mavridou vd. (2010) [5], Tablo 6a–6b (makaledeki Şekil 8'in veri kaynağı). Çukurcuklu borularda Δp/Δp₀ "
       "makalede 0.8–1.1 aralığı olarak verilmiştir. Grafik bu çalışmada çizilmiştir.")


# Şekil E — Kendi ORC hesaplarımız: T–s diyagramları
def doyma_egrisi(ak, n=120):
    Tt, Tc = CP.PropsSI("Ttriple", ak), CP.PropsSI("Tcrit", ak)
    T = np.linspace(max(Tt, 250), Tc - 0.05, n)
    sl = [CP.PropsSI("S", "T", t, "Q", 0, ak) for t in T]
    sv = [CP.PropsSI("S", "T", t, "Q", 1, ak) for t in T]
    return np.r_[sl, sv[::-1]] / 1e3, np.r_[T, T[::-1]] - 273.15


def cevrim_egrisi(c, ak):
    pl, ph = c["p"]
    h = c["durumlar_h"]
    yol = []
    for hh in np.linspace(h["2"], h["3"], 60):
        yol.append((CP.PropsSI("S", "P", ph, "H", hh, ak), CP.PropsSI("T", "P", ph, "H", hh, ak)))
    # gerçek genleşme yolu bilinmediğinden 3→4 düz çizgiyle gösterilmiştir
    yol.append((CP.PropsSI("S", "P", pl, "H", h["4"], ak), CP.PropsSI("T", "P", pl, "H", h["4"], ak)))
    for hh in np.linspace(h["4"], h["1"], 60):
        yol.append((CP.PropsSI("S", "P", pl, "H", hh, ak), CP.PropsSI("T", "P", pl, "H", hh, ak)))
    yol.append((CP.PropsSI("S", "P", ph, "H", h["2"], ak), CP.PropsSI("T", "P", ph, "H", h["2"], ak)))
    s, T = np.array(yol).T
    return s / 1e3, T - 273.15


ADLAR = {"R245fa": "R245fa", "Ethanol": "Etanol", "Toluene": "Toluen", "Water": "Su (buhar Rankine)"}
fig, axs = plt.subplots(2, 2, figsize=(10, 8))
for ax, c in zip(axs.flat, cevrimler):
    ak = c["akiskan"]
    s_d, T_d = doyma_egrisi(ak)
    ax.plot(s_d, T_d, "k-", lw=1, label="Doyma eğrisi")
    s_c, T_c = cevrim_egrisi(c, ak)
    ax.plot(s_c, T_c, "-", color=RENK[0], lw=2, label="Çevrim")
    for k in "1234":
        ax.plot(c["durumlar_s"][k] / 1e3, c["durumlar_T_C"][k], "o", color=RENK[3])
        ax.annotate(k, (c["durumlar_s"][k] / 1e3, c["durumlar_T_C"][k]), textcoords="offset points", xytext=(5, 4))
    ax.set_title(f"{ADLAR[ak]}: Ẇnet={c['W_net_kW']:.1f} kW, ηth=%{100 * c['eta_th']:.1f}", fontsize=9.5)
    ax.set_xlabel("Özgül entropi s [kJ/kg·K]")
    ax.set_ylabel("Sıcaklık T [°C]")
    ax.legend(fontsize=7.5, loc="upper left")
plt.suptitle("Basit Rankine/ORC çevrimlerinin T–s diyagramları (bu çalışmada hesaplanmıştır)", y=1.01)
plt.tight_layout()
kaydet("sekil07_Ts_kendi_hesap.png",
       "BU ÇALIŞMADA YAPILAN HESAP (literatür sonucu değildir). Isı kaynağı: Mavridou vd. (2010) [5] Tablo 1, %100 yük/1300 rpm "
       "(503.5 °C, 0.49 kg/s). Varsayımlar: ηgenleştirici=0.70, ηpompa=0.60, Tkond=50 °C, pinch=30 K, egzoz çıkışı ≥120 °C. "
       "Özellikler: CoolProp 8.0. Su çevrimi Mavridou Tablo 2 koşullarında (33 bar, 394.2 °C) kurulmuştur.")

# Şekil F — R245fa P–h diyagramı
c = cevrimler[0]
ak = "R245fa"
Tt, Tc = 250.0, CP.PropsSI("Tcrit", ak) - 0.05
T = np.linspace(Tt, Tc, 150)
plt.figure(figsize=(7, 4.6))
plt.semilogy([CP.PropsSI("H", "T", t, "Q", 0, ak) / 1e3 for t in T], [CP.PropsSI("P", "T", t, "Q", 0, ak) / 1e5 for t in T], "k-", lw=1)
plt.semilogy([CP.PropsSI("H", "T", t, "Q", 1, ak) / 1e3 for t in T], [CP.PropsSI("P", "T", t, "Q", 1, ak) / 1e5 for t in T], "k-", lw=1, label="Doyma eğrisi")
hs = c["durumlar_h"]
pl, ph = c["p"]
H = [hs["1"], hs["2"], hs["3"], hs["4"], hs["1"]]
P = [pl, ph, ph, pl, pl]
plt.semilogy(np.array(H) / 1e3, np.array(P) / 1e5, "o-", color=RENK[0], lw=2, label="R245fa ORC")
for k, hh, pp in zip("1234", H, P):
    plt.annotate(k, (hh / 1e3, pp / 1e5), textcoords="offset points", xytext=(5, 5))
plt.xlabel("Özgül entalpi h [kJ/kg]")
plt.ylabel("Basınç P [bar]")
plt.legend()
plt.title("R245fa ORC P–h diyagramı (Tbuh=140 °C, Tkond=50 °C)")
kaydet("sekil08_Ph_R245fa.png",
       "BU ÇALIŞMADA YAPILAN HESAP. Durumlar: 1 pompa girişi, 2 pompa çıkışı, 3 genleştirici girişi, 4 genleştirici çıkışı. "
       "Akışkan özellikleri CoolProp 8.0.")

# Şekil G — duyarlılık
fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
for i, (ak, v) in enumerate(duyar.items()):
    Ts = [t for t, _ in v]
    ax[0].plot(Ts, [cc["W_net_kW"] for _, cc in v], "o-", color=RENK[i], label=ADLAR[ak])
    ax[1].plot(Ts, [100 * cc["eta_th"] for _, cc in v], "o-", color=RENK[i], label=f"{ADLAR[ak]} ηth")
    ax[1].plot(Ts, [100 * cc["eta_II_toplam"] for _, cc in v], "s--", color=RENK[i], label=f"{ADLAR[ak]} ηII")
ax[0].set_xlabel("Buharlaşma sıcaklığı [°C]")
ax[0].set_ylabel("Net güç [kW]")
ax[0].legend()
ax[0].set_title("(a) Net güç")
ax[1].set_xlabel("Buharlaşma sıcaklığı [°C]")
ax[1].set_ylabel("Verim [%]")
ax[1].legend(fontsize=7.5)
ax[1].set_title("(b) Isıl ve ekserji verimi")
kaydet("sekil09_duyarlilik.png",
       "BU ÇALIŞMADA YAPILAN HESAP. ηII = Ẇnet / egzozun 25 °C ölü hale göre termal ekserjisi. Diğer varsayımlar Şekil 7 ile aynıdır.")

# Şekil H — Literatürde raporlanan kazanımlar (metrik türüne göre ayrılmış)
lit_a = [  # yakıt tüketimi / BSFC iyileşmesi [%]
    ("Park vd. 2011 [9]\nORC (etanol), 10.8 L HD dizel, deney", 3, 5),
    ("Hossain & Bari 2013 [34]\nsu Rankine, 40 kW jeneratör, bsfc", 12, 12),
    ("Pasini vd. 2016 [7]\nE-turbokompaund, 0.9 L SI, BSFC", 0, 4),
    ("Pasini vd. 2016 [7]\nE-turbokompaund, araç çevrimi", 0, 2.7),
    ("Ricardo TERS (Lion vd. 2017 [6])\nORC R245fa, hibrit otobüs", 2.7, 6),
]
lit_b = [  # güç veya ısıl verim artışı [%]
    ("Endo vd. 2007 [20] (Honda)\nbuhar Rankine, 100 km/h, ηth göreli", 13.2, 13.2),
    ("Vaja & Gambarotta 2010 [11]\nORC, sabit motor, toplam verim", 12, 12),
    ("Yu vd. 2013 [10]\nR245fa ORC, dizel, ηth (simül.)", 6.1, 6.1),
    ("Galindo vd. 2015 [35]\nORC (etanol), 2 L benzinli, güç", 3.7, 3.7),
    ("Hossain & Bari 2013 [34]\nsu Rankine, ek güç", 11, 11),
    ("Bari & Hossain 2013 [43]\noptimize HEX, ek güç", 16, 23.7),
]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8))
for ax, veri, bas in ((axs[0], lit_a, "(a) Yakıt tüketimi / BSFC iyileşmesi [%]"),
                      (axs[1], lit_b, "(b) Güç veya verim artışı [%]")):
    for i, (ad, a, b) in enumerate(veri):
        if a == b:
            ax.plot(a, i, "o", color=RENK[0], ms=8)
        else:
            ax.plot([a, b], [i, i], "-", color=RENK[1], lw=6, solid_capstyle="butt")
        ax.text(max(a, b) + 0.4, i, f"{a:g}" if a == b else f"{a:g}–{b:g}", va="center", fontsize=8)
    ax.set_yticks(range(len(veri)), [v[0] for v in veri], fontsize=7.5)
    ax.set_title(bas, fontsize=10)
    ax.set_xlim(0, 27)
plt.tight_layout()
kaydet("sekil10_literatur_kazanimlar.png",
       "Veriler belirtilen yayınların özetlerinden/sonuç bölümlerinden aktarılmıştır. Çalışma koşulları (motor, yük, çevrim, deney/simülasyon) "
       "farklı olduğundan değerler doğrudan eşdeğer değildir; yalnızca büyüklük mertebesini göstermek içindir. Grafik bu çalışmada çizilmiştir.")

# Şekil I — TEG verimi (ZT etkisi)
ZT = np.linspace(0.2, 2.5, 60)
plt.figure(figsize=(7, 4))
for i, (th, tc) in enumerate(((250, 50), (300, 80), (400, 80))):
    plt.plot(ZT, [100 * teg_verim(th + 273.15, tc + 273.15, z) for z in ZT], color=RENK[i], label=f"Th={th} °C, Tc={tc} °C")
plt.axhline(2.8, color="k", ls=":", lw=1)
plt.text(0.25, 3.0, "Kim vd. (2016) [13] ölçülen azami dönüşüm verimi: %2.8", fontsize=8)
plt.xlabel("Boyutsuz başarım katsayısı ZT [–]")
plt.ylabel("Modül dönüşüm verimi [%]")
plt.legend()
plt.title("Termoelektrik modülün kuramsal verimi")
kaydet("sekil11_teg_verim.png",
       "BU ÇALIŞMADA YAPILAN HESAP: η = (ΔT/Th)·(√(1+ZT)−1)/(√(1+ZT)+Tc/Th). Karşılaştırma noktası Kim vd. (2016) [13] özetinden alınmıştır.")

# Şekil J — Güç türbini kaba kestirimi
plt.figure(figsize=(7, 4))
for i, (r, lab) in enumerate(((MAV_T1[0], "%100 yük, 1300 rpm"), (MAV_T1[4], "%100 yük, 1700 rpm"), (MAV_T1[2], "%50 yük, 1300 rpm"))):
    plt.plot(PRs, [guc_turbini(r[2], r[4], p) for p in PRs], color=RENK[i], label=lab)
plt.xlabel("Güç türbini genleşme oranı [–]")
plt.ylabel("Türbin mili gücü [kW]")
plt.legend()
plt.title("Seri güç türbininde elde edilebilecek brüt güç (ters basınç cezası hariç)")
kaydet("sekil12_guc_turbini.png",
       "BU ÇALIŞMADA YAPILAN HESAP: Ẇ = ṁ·cp·Tgiriş·ηT·[1−PR^(−(γ−1)/γ)], ηT=0.70, γ=1.34. Egzoz koşulları Mavridou vd. (2010) [5] Tablo 1. "
       "Brüt değerdir; artan ters basıncın motor pompalama işine etkisi (bkz. Pasini vd. [7]) düşülmemiştir.")

# Şekil K — Sistem şeması (Mavridou Şekil 1 anlatımına dayanarak yeniden çizilmiştir)
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_axis_off()
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)


def kutu(x, y, w, h, t, r="#e8eef4"):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=r, ec="k"))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.5)


def ok(x1, y1, x2, y2, r="k", t=None):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color=r, lw=1.6))
    if t:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, t, fontsize=7.5, color=r, ha="center")


kutu(0.3, 3.9, 1.8, 1.3, "Dizel motor\n362 kW")
kutu(2.7, 4.7, 1.5, 0.8, "Turbo-\nşarj")
kutu(4.8, 4.7, 1.6, 0.8, "Partikül\nfiltresi")
kutu(7.0, 4.5, 2.2, 1.1, "Egzoz HEX: ön ısıtıcı\n+ buharlaştırıcı\n+ kızdırıcı", "#f6e3cf")
kutu(7.0, 2.9, 2.2, 0.9, "EGR soğutucu\n(ek kızdırma)", "#f6e3cf")
kutu(7.0, 1.3, 2.2, 0.9, "Pistonlu genleştirici\n+ jeneratör", "#dcefd9")
kutu(4.0, 0.2, 2.2, 0.8, "Yoğuşturucu\n(2. radyatör)", "#dde7f5")
kutu(0.6, 0.2, 2.4, 0.8, "Besleme pompası\n(pozitif yer değiştirmeli)", "#dde7f5")
ok(2.1, 4.9, 2.7, 5.1, RENK[3])
ax.text(2.2, 5.25, "egzoz", fontsize=7.5, color=RENK[3])
ok(4.2, 5.1, 4.8, 5.1, RENK[3])
ok(6.4, 5.1, 7.0, 5.1, RENK[3])
ok(9.2, 5.1, 9.8, 5.1, RENK[3])
ax.text(9.3, 5.25, "baca", fontsize=7.5, color=RENK[3])
ax.plot([1.2, 1.2, 6.0, 6.0], [3.9, 3.35, 3.35, 3.35], color=RENK[3], lw=1.6)
ok(6.0, 3.35, 7.0, 3.35, RENK[3])
ax.text(2.4, 3.45, "EGR gazı (yüksek basınç hattı)", fontsize=7.5, color=RENK[3])
ax.plot([1.8, 1.8, 6.6, 6.6], [1.0, 2.6, 2.6, 4.9], color=RENK[0], lw=1.6)
ok(6.6, 4.9, 7.0, 4.9, RENK[0])
ax.text(2.0, 2.7, "su, 90.6 °C / 33 bar (Tablo 2)", fontsize=7.5, color=RENK[0])
ok(8.1, 4.5, 8.1, 3.8, RENK[0])
ax.text(8.2, 4.1, "kızgın buhar 394.2 °C (Tablo 2)", fontsize=7.5, color=RENK[0])
ok(8.1, 2.9, 8.1, 2.2, RENK[0])
ax.text(8.2, 2.5, "EGR ısısıyla ek kızdırma", fontsize=7.5, color=RENK[0])
ax.plot([8.1, 8.1, 5.1], [1.3, 0.6, 0.6], color=RENK[0], lw=1.6, alpha=0)
ok(7.0, 1.5, 6.2, 0.7, RENK[0])
ok(4.0, 0.6, 3.0, 0.6, RENK[0])
ax.set_title("Ağır vasıta dizel motoru için su-buharlı alt (bottoming) Rankine çevrimi yerleşimi", fontsize=10)
kaydet("sekil04_sistem_semasi.png",
       "Mavridou vd. (2010) [5] Şekil 1 ve Bölüm 2'deki anlatıma dayanarak bu çalışmada yeniden çizilmiş ŞEMATİK gösterimdir (orijinal şekil değildir). "
       "Sıcaklık/basınç değerleri aynı makalenin Tablo 2'sinden alınmıştır.")

# Şekil L — Çalışmanın yöntem akış şeması
ADIMLAR = [
    ("ADIM 1", "Literatür taraması", "Crossref, OpenAlex, Semantic Scholar, SAE Mobilus,\nkurumsal arşivler; 2006–2024; anahtar kelime sorguları"),
    ("ADIM 2", "Kaynak doğrulama ve seçim", "DOI çözümleme, yazar/cilt/sayfa kontrolü;\nkonu, sayısal veri ve yayın türü ölçütleri → 52 kaynak"),
    ("ADIM 3", "Veri çıkarımı [L]", "Özet ve açık erişimli tam metinlerden sayısal bulgular,\norijinal tablo/şekil numaraları, tasarım parametreleri"),
    ("ADIM 4", "Bağımsız doğrulama [H]", "Mavridou vd. [5] Tablo 2 verisiyle LMTD, UA ve\nIAPWS-95 su tarafı enerji dengesi"),
    ("ADIM 5", "Çevrim analizi [H]", "R245fa / etanol / toluen / su için enerji ve ekserji analizi,\nyoğuşma ve buharlaşma sıcaklığı duyarlılığı (CoolProp)"),
    ("ADIM 6", "Karşılaştırma ve değerlendirme", "Literatür sonuçlarının ölçüt türüne göre karşılaştırılması,\nçelişkilerin nedenleri, uygulanabilirlik ve öneriler"),
]
fig, ax = plt.subplots(figsize=(8, 5.4))
ax.set_axis_off()
ax.set_xlim(0, 10)
ax.set_ylim(0.1, len(ADIMLAR) * 1.2)
for i, (no, bas, acik) in enumerate(ADIMLAR):
    y = (len(ADIMLAR) - 1 - i) * 1.2 + 0.15
    renk = "#e8eef4" if "[H]" not in bas else "#dcefd9"
    ax.add_patch(plt.Rectangle((0.3, y), 9.4, 0.85, fc=renk, ec="#1f3b57", lw=1.2))
    ax.add_patch(plt.Rectangle((0.3, y), 1.4, 0.85, fc="#1f3b57", ec="#1f3b57"))
    ax.text(1.0, y + 0.425, no, color="white", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(1.95, y + 0.6, bas, ha="left", va="center", fontsize=10, fontweight="bold", color="#1f3b57")
    ax.text(1.95, y + 0.27, acik, ha="left", va="center", fontsize=7.8, color="#333333")
    if i < len(ADIMLAR) - 1:
        ax.annotate("", xy=(5.0, y - 0.33), xytext=(5.0, y), arrowprops=dict(arrowstyle="-|>", color="#1f3b57", lw=1.4))
plt.gca().grid(False)
plt.savefig(os.path.join(SEKIL, "sekil03_yontem_akisi.png"))
plt.close()

with open(os.path.join(BURADA, "sonuclar.json"), "w", encoding="utf-8") as f:
    json.dump(SONUC, f, ensure_ascii=False, indent=1, default=float)
print(json.dumps(SONUC, ensure_ascii=False, indent=1, default=float))
