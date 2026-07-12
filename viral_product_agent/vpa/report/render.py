"""Rapor cikti: ayni Report nesnesinden JSON (makine) + Markdown/Turkce (insan)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..models import Report


def write(report: Report, output_dir: Path, date_str: str) -> tuple[Path, Path]:
    json_path = output_dir / f"{date_str}_report.json"
    md_path = output_dir / f"{date_str}_report.md"
    json_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    return json_path, md_path


def _markdown(r: Report) -> str:
    lines = [
        f"# Türkiye Viral Ürün Adayları — {r.generated_at}",
        "",
        "> Bu rapor karar-destek amaçlıdır: viralite doğası gereği düşük kesinliklidir;",
        "> maliyet/marj rakamları tahmindir, satın alma kararı öncesi manuel doğrulayın.",
        "",
        "## Kaynak durumu",
        "",
        "| Kaynak | Durum |",
        "|---|---|",
    ]
    for src, status in r.source_status.items():
        lines.append(f"| {src} | {status} |")
    if r.notes:
        lines += ["", "## Notlar", ""] + [f"- {n}" for n in r.notes]

    lines += ["", "## Sıralı aday listesi", ""]
    for i, c in enumerate(r.ranked, 1):
        conf = "" if c.availability_confidence == "high" else " ⚠️ *TR kontrolü düşük güven — manuel doğrula*"
        lines += [
            f"### {i}. {c.title} — skor {c.final_score:.2f}{conf}",
            "",
            f"- **Ne:** {c.description or '-'}",
            f"- **Kaynak:** [{c.source}]({c.url})" + (
                f" (+{len(c.also_seen)} kaynakta daha görüldü)" if c.also_seen else ""),
            f"- **Tahmini fiyat (USD):** {c.price_usd if c.price_usd is not None else 'bilinmiyor'}",
            f"- **Sinyaller:** " + ", ".join(f"{k}={v:.2f}" for k, v in c.signals.items()),
        ]
        if c.llm_scores:
            lines.append("- **LLM boyutları:** " + ", ".join(
                f"{k}={v:.0f}/10" for k, v in c.llm_scores.items()))
        if c.llm_rationale:
            lines.append("- **Neden viral olabilir:** " +
                         c.llm_rationale.get("demonstrability", "") + " " +
                         c.llm_rationale.get("problem_or_emotion", ""))
        lines.append("")

    if r.ads:
        lines += ["## Reklam konseptleri (top ürünler)", ""]
        for ad in r.ads:
            lines += [
                f"### {ad.product_title}",
                "",
                f"- **Kanca:** {ad.hook}",
                f"- **15sn video:** {ad.video_script}",
                f"- **Platform:** {ad.platform}",
                f"- **Hedef kitle:** {ad.audience}",
            ]
            if ad.note:
                lines.append(f"- **Not:** {ad.note}")
            lines.append("")

    if r.eliminated:
        lines += ["## Elenenler (Türkiye'de zaten yaygın)", ""]
        for c in r.eliminated:
            lines.append(f"- {c.title} — {c.elimination_reason}")
        lines.append("")
    return "\n".join(lines)
