"""Report/Candidate/AdConcept -> Telegram HTML metni.

Telegram HTML parse_mode yalnizca birkac etiket destekler (<b>,<i>,<code>,<a>);
tum dinamik metin escape edilir. Mesajlar 4096 karakter sinirina kirpilir."""
from __future__ import annotations

from ..models import AdConcept, Candidate, Report

TG_LIMIT = 4096


def esc(text: str) -> str:
    """Telegram HTML icin kacis (yalnizca & < > )."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def clip(text: str, limit: int = TG_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_summary(report: Report) -> str:
    """Tarama ozeti: tarih, gecen/elenen sayilari, kaynak durumu, notlar."""
    lines = [f"<b>🇹🇷 Viral Ürün Taraması — {esc(report.generated_at)}</b>", ""]
    lines.append(f"✅ Aday: <b>{len(report.ranked)}</b>   ❌ Elenen: <b>{len(report.eliminated)}</b>")
    ok = sum(1 for s in report.source_status.values() if s.startswith("ok"))
    lines.append(f"📡 Kaynak: {ok}/{len(report.source_status)} aktif")
    if report.notes:
        lines += ["", "<i>" + esc(report.notes[0]) + "</i>"]
    lines += ["", "Detay için aşağıdaki ürünlere dokun 👇"]
    return clip("\n".join(lines))


def format_candidate(c: Candidate, index: int) -> str:
    """Tek urunun detay karti (foto caption'i veya mesaj govdesi)."""
    conf = "" if c.availability_confidence == "high" else "  ⚠️ <i>TR kontrolü düşük güven</i>"
    lines = [
        f"<b>{index}. {esc(c.title)}</b> — skor {c.final_score:.2f}{conf}",
        "",
    ]
    if c.description:
        lines.append(esc(clip(c.description, 400)))
        lines.append("")
    if c.price_usd is not None:
        lines.append(f"💵 Tahmini maliyet: ~${esc(c.price_usd)}")
    if c.signals:
        sig = ", ".join(f"{esc(k)}={v:.2f}" for k, v in c.signals.items())
        lines.append("📊 " + sig)
    if c.llm_scores:
        lines.append("🤖 " + ", ".join(f"{esc(k)}={v:.0f}/10" for k, v in c.llm_scores.items()))
    why = " ".join(v for v in (c.llm_rationale.get("demonstrability", ""),
                               c.llm_rationale.get("problem_or_emotion", "")) if v)
    if why:
        lines += ["", "<b>Neden viral olabilir:</b> " + esc(clip(why, 500))]
    if c.url:
        lines += ["", f"🔗 <a href=\"{esc(c.url)}\">Kaynak</a>"]
    return clip("\n".join(lines), 1024)  # foto caption siniri 1024


def format_ad(ad: AdConcept) -> str:
    """Reklam konsepti karti."""
    lines = [f"<b>📣 Reklam konsepti — {esc(ad.product_title)}</b>", ""]
    if ad.hook:
        lines.append(f"<b>Kanca:</b> {esc(ad.hook)}")
    if ad.video_script:
        lines += ["", f"<b>15sn video:</b> {esc(ad.video_script)}"]
    if ad.platform:
        lines += ["", f"<b>Platform:</b> {esc(ad.platform)}"]
    if ad.audience:
        lines.append(f"<b>Hedef kitle:</b> {esc(ad.audience)}")
    if ad.note:
        lines += ["", "<i>" + esc(ad.note) + "</i>"]
    return clip("\n".join(lines))
