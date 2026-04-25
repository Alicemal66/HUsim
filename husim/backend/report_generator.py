"""PDF rapor üretici — ReportLab kullanır"""
import io
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False
    logger.warning("ReportLab kurulu değil — PDF üretimi devre dışı.")


REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def generate_pdf(
    simulation_id: str,
    scenario_id: str,
    metrics: dict,
    weather: dict | None,
    include_metrics: bool = True,
    include_weather: bool = True,
) -> bytes:
    """Simülasyon sonuçlarından PDF rapor üret."""
    if not REPORTLAB_OK:
        return _generate_text_report(simulation_id, scenario_id, metrics, weather)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "husim_title",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#1a3a5c"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "husim_heading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "husim_body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )

    story = []

    # Başlık
    story.append(Paragraph("HÜsim — Simülasyon Raporu", title_style))
    story.append(Paragraph(f"Simülasyon Kimliği: {simulation_id}", body_style))
    story.append(Paragraph(f"Senaryo: {scenario_id}", body_style))
    story.append(Paragraph(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", body_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a3a5c")))
    story.append(Spacer(1, 12))

    # Hava koşulları
    if include_weather and weather:
        story.append(Paragraph("Hava Koşulları", heading_style))
        weather_data = [
            ["Parametre", "Değer"],
            ["Hava Tipi", _tr_weather(weather.get("weather_type", ""))],
            ["Sıcaklık", f"{weather.get('temperature', 0)} °C"],
            ["Rüzgar Hızı", f"{weather.get('wind_speed', 0)} km/h"],
            ["Görüş Mesafesi", f"{weather.get('visibility', 0)} m"],
            ["Zemin Durumu", _tr_ground(weather.get("ground_type", ""))],
        ]
        story.append(_make_table(weather_data))
        story.append(Spacer(1, 8))

    # Metrikler
    if include_metrics and metrics:
        story.append(Paragraph("Simülasyon Metrikleri", heading_style))

        # Güvenlik
        story.append(Paragraph("Güvenlik", ParagraphStyle("sub", parent=body_style, fontSize=11, textColor=colors.HexColor("#ef4444"))))
        safety_data = [
            ["Metrik", "Değer"],
            ["Çarpışma Sayısı", str(metrics.get("collision_count", 0))],
            ["Yakın Geçiş Sayısı", str(metrics.get("near_miss_count", 0))],
            ["Min. Güvenlik Mesafesi", f"{metrics.get('min_safety_distance', 0)} m"],
            ["Risk Skoru", f"{metrics.get('risk_score', 0)}/100"],
        ]
        story.append(_make_table(safety_data))
        story.append(Spacer(1, 8))

        # Verimlilik
        story.append(Paragraph("Verimlilik", ParagraphStyle("sub2", parent=body_style, fontSize=11, textColor=colors.HexColor("#10b981"))))
        efficiency_data = [
            ["Metrik", "Değer"],
            ["Tamamlanma Süresi", f"{metrics.get('completion_time', 0)} sn"],
            ["Güzergah Verimliliği", f"%{round(metrics.get('path_efficiency', 0) * 100, 1)}"],
            ["Ortalama Hız", f"{metrics.get('average_speed', 0)} m/s"],
        ]
        story.append(_make_table(efficiency_data))
        story.append(Spacer(1, 8))

        # Görev tamamlama
        completed = metrics.get("task_completed", False)
        story.append(Paragraph(
            f"Görev Durumu: {'✓ TAMAMLANDI' if completed else '✗ BAŞARISIZ'}",
            ParagraphStyle("result", parent=body_style, fontSize=12,
                           textColor=colors.green if completed else colors.red)
        ))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Algoritma: {metrics.get('algorithm_name', '')}", body_style))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray))
    story.append(Paragraph("HÜsim — Maden Simülasyon Kontrol Sistemi", body_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Diske kaydet
    output_file = REPORTS_DIR / f"rapor_{simulation_id}.pdf"
    output_file.write_bytes(pdf_bytes)
    logger.info(f"PDF rapor oluşturuldu: {output_file}")

    return pdf_bytes


def _make_table(data: list[list]) -> Table:
    """Şık bir tablo oluştur."""
    table = Table(data, colWidths=[8 * cm, 8 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _tr_weather(key: str) -> str:
    return {"clear": "Açık", "cloudy": "Bulutlu", "rainy": "Yağmurlu",
            "snowy": "Karlı", "foggy": "Sisli", "stormy": "Fırtınalı"}.get(key, key)


def _tr_ground(key: str) -> str:
    return {"dry": "Kuru", "wet": "Islak", "muddy": "Çamurlu",
            "snowy": "Karlı", "icy": "Buzlu"}.get(key, key)


def _generate_text_report(simulation_id, scenario_id, metrics, weather) -> bytes:
    """ReportLab yoksa basit metin raporu döndür."""
    lines = [
        "HÜsim - Simülasyon Raporu",
        "=" * 40,
        f"Simülasyon Kimliği: {simulation_id}",
        f"Senaryo: {scenario_id}",
        f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "",
        "Metrikler:",
        json.dumps(metrics, ensure_ascii=False, indent=2),
    ]
    if weather:
        lines += ["", "Hava Koşulları:", json.dumps(weather, ensure_ascii=False, indent=2)]
    return "\n".join(lines).encode("utf-8")
