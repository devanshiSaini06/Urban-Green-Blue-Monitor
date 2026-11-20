"""
PDF report generation module for Urban Green and Blue Change Monitor.
Generates comprehensive reports with methodology, charts, maps, and findings.
"""
import base64
import io
import textwrap
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.lib.colors import Color

from config import (
    STUDY_YEARS, SEASON_WINDOWS, SENTINEL_COLLECTION,
    EXPORT_CRS, GEE_PROJECT_ID, REPORT_FOOTER_TEXT
)
from schemas import ReportRequest, AnalysisResponse, YearlyStats, QualityFlags


# Color palette (color-blind safe)
COLORS = {
    'primary': HexColor('#16a34a'),
    'water': HexColor('#0ea5e9'),
    'vegetation': HexColor('#22c55e'),
    'built': HexColor('#737373'),
    'other': HexColor('#a3a3a3'),
    'text': HexColor('#1f2937'),
    'text_light': HexColor('#6b7280'),
    'bg_light': HexColor('#f9fafb'),
    'border': HexColor('#e5e7eb'),
    'warning': HexColor('#f59e0b'),
    'danger': HexColor('#ef4444'),
}


@dataclass
class ReportData:
    """Container for all data needed to generate report."""
    analysis: AnalysisResponse
    request: ReportRequest
    charts: Dict[str, bytes]  # base64 encoded chart images


def create_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        leading=28,
        textColor=COLORS['primary'],
        spaceAfter=6,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        textColor=COLORS['text_light'],
        spaceAfter=20,
    ))

    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=COLORS['primary'],
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=COLORS['text'],
        spaceBefore=10,
        spaceAfter=6,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=COLORS['text'],
        spaceAfter=6,
        alignment=TA_JUSTIFY,
    ))

    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=COLORS['text_light'],
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=COLORS['text'],
    ))

    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=white,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='Caption',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=COLORS['text_light'],
        alignment=TA_CENTER,
        spaceBefore=2,
        spaceAfter=8,
    ))

    return styles


def create_chart_image(chart_data: Dict[str, Any], chart_type: str = 'line') -> bytes:
    """Create chart image from data using reportlab graphics."""
    drawing = Drawing(400, 250)

    if chart_type == 'line':
        chart = HorizontalLineChart()
        chart.x = 50
        chart.y = 50
        chart.width = 300
        chart.height = 150
        chart.data = chart_data.get('data', [])
        chart.categoryAxis.categoryNames = chart_data.get('labels', [])
        chart.categoryAxis.labels.fontSize = 8
        chart.valueAxis.valueMin = chart_data.get('min', 0)
        chart.valueAxis.valueMax = chart_data.get('max', 100)
        chart.valueAxis.valueStep = chart_data.get('step', 20)
        chart.valueAxis.labels.fontSize = 8

        # Style lines
        colors_list = [COLORS['vegetation'], COLORS['water'], COLORS['built']]
        for i, line in enumerate(chart.lines):
            line.strokeColor = colors_list[i % len(colors_list)]
            line.strokeWidth = 2
            line.symbol = None

        # Legend
        legend = Legend()
        legend.x = 360
        legend.y = 150
        legend.alignment = 'right'
        legend.fontSize = 8
        legend.colorNamePairs = zip(
            colors_list[:len(chart_data.get('series', []))],
            chart_data.get('series', [])
        )
        drawing.add(legend)

    elif chart_type == 'bar':
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.width = 300
        chart.height = 150
        chart.data = chart_data.get('data', [])
        chart.categoryAxis.categoryNames = chart_data.get('labels', [])
        chart.categoryAxis.labels.fontSize = 8
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = chart_data.get('max', 100)
        chart.valueAxis.valueStep = chart_data.get('step', 20)
        chart.valueAxis.labels.fontSize = 8
        chart.bars[0].fillColor = COLORS['primary']

    drawing.add(chart)

    # Render to bytes
    buffer = io.BytesIO()
    drawing.save(formats=['png'], outDir='.', fnRoot='temp_chart')
    # Note: In production, use reportlab.graphics.renderPM.drawToString
    # For now, return placeholder
    return b''


def generate_findings_text(analysis: AnalysisResponse) -> List[str]:
    """Generate plain-language findings from computed numbers."""
    findings = []

    if len(analysis.stats) < 2:
        return ["Insufficient data for change analysis. At least two years required."]

    first = analysis.stats[0]
    last = analysis.stats[-1]

    # Vegetation change
    veg_change_km2 = last.vegetation_km2 - first.vegetation_km2
    veg_change_pct = (veg_change_km2 / first.vegetation_km2 * 100) if first.vegetation_km2 > 0 else 0
    veg_direction = "gain" if veg_change_km2 > 0 else "loss"
    findings.append(
        f"Vegetation cover {veg_direction}: {abs(veg_change_km2):.2f} km² "
        f"({abs(veg_change_pct):.1f}%) between {first.year} and {last.year}."
    )

    # Water change
    water_change_km2 = last.water_km2 - first.water_km2
    water_change_pct = (water_change_km2 / first.water_km2 * 100) if first.water_km2 > 0 else 0
    water_direction = "gain" if water_change_km2 > 0 else "loss"
    findings.append(
        f"Surface water {water_direction}: {abs(water_change_km2):.2f} km² "
        f"({abs(water_change_pct):.1f}%) between {first.year} and {last.year}."
    )

    # Built-up change
    built_change_km2 = last.built_bare_km2 - first.built_bare_km2
    built_change_pct = (built_change_km2 / first.built_bare_km2 * 100) if first.built_bare_km2 > 0 else 0
    built_direction = "gain" if built_change_km2 > 0 else "loss"
    findings.append(
        f"Built-up/bare land {built_direction}: {abs(built_change_km2):.2f} km² "
        f"({abs(built_change_pct):.1f}%) between {first.year} and {last.year}."
    )

    # NDVI change
    ndvi_change = last.mean_ndvi - first.mean_ndvi
    ndvi_direction = "increase" if ndvi_change > 0 else "decrease"
    findings.append(
        f"Mean NDVI {ndvi_direction}: {abs(ndvi_change):.3f} "
        f"({first.mean_ndvi:.3f} → {last.mean_ndvi:.3f})."
    )

    # Quality warnings
    quality = analysis.quality_summary
    if quality.get('years_with_warnings', 0) > 0:
        findings.append(
            f"Data quality warning: {quality['years_with_warnings']} year(s) have low image count "
            f"or coverage. Interpret changes in those years with caution."
        )

    if quality.get('outlier_years'):
        findings.append(
            f"Outlier detected in year(s): {', '.join(map(str, quality['outlier_years']))}. "
            f"These years differ from neighbors by more than 25% and may be artifacts."
        )

    if len(analysis.stats) >= 3:
        findings.append(
            f"Trend analysis across {len(analysis.stats)} years (n={len(analysis.stats)}) has "
            f"very low statistical power. Any reported 'significant' trends should be "
            f"interpreted as exploratory only."
        )

    return findings


def build_report(data: ReportData) -> bytes:
    """Build the complete PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = create_styles()
    story = []

    analysis = data.analysis
    request = data.request

    # =========================================================================
    # TITLE PAGE
    # =========================================================================
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph("Urban Green and Blue Change Monitor", styles['CustomTitle']))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Land Cover Change Analysis: {analysis.stats[0].year}–{analysis.stats[-1].year}",
        styles['CustomSubtitle']
    ))
    story.append(Spacer(1, 1*cm))

    # District info
    district_name = "Custom Area"
    if request.district_id:
        if request.district_id == "bengaluru_urban":
            district_name = "Bengaluru Urban (Karnataka)"
        elif request.district_id == "gautam_buddha_nagar":
            district_name = "Gautam Buddha Nagar / Greater Noida (Uttar Pradesh)"

    story.append(Paragraph(f"<b>Study Area:</b> {district_name}", styles['BodyText2']))
    story.append(Paragraph(f"<b>Seasonal Window:</b> {analysis.season['name']}", styles['BodyText2']))
    story.append(Paragraph(f"<b>Classifier:</b> {analysis.classifier}", styles['BodyText2']))
    story.append(Paragraph(f"<b>Analysis Scale:</b> {analysis.scale} m", styles['BodyText2']))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles['BodyText2']))
    story.append(Paragraph(f"<b>GEE Project:</b> {GEE_PROJECT_ID}", styles['BodyText2']))

    story.append(PageBreak())

    # =========================================================================
    # EXECUTIVE SUMMARY
    # =========================================================================
    story.append(Paragraph("Executive Summary", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['primary']))
    story.append(Spacer(1, 0.3*cm))

    findings = generate_findings_text(analysis)
    for finding in findings:
        story.append(Paragraph(f"• {finding}", styles['BodyText2']))

    story.append(PageBreak())

    # =========================================================================
    # METHODOLOGY
    # =========================================================================
    story.append(Paragraph("Methodology", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['primary']))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("Data Source", styles['SubsectionHeader']))
    story.append(Paragraph(
        f"Sentinel-2 Surface Reflectance Harmonized ({SENTINEL_COLLECTION}) "
        f"filtered to cloud cover < {request.cloud_threshold}%, "
        f"seasonal window {request.season['name']} for each year.",
        styles['BodyText2']
    ))

    story.append(Paragraph("Preprocessing", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Cloud masking using Scene Classification Layer (SCL): classes 0, 1, 3, 8, 9, 10, 11 removed. "
        "Bands B2, B3, B4, B8, B11, B12 scaled by 0.0001. "
        f"Annual composite: median of masked images clipped to district boundary. "
        f"Analysis scale: {analysis.scale} m, projection {EXPORT_CRS}.",
        styles['BodyText2']
    ))

    story.append(Paragraph("Spectral Indices", styles['SubsectionHeader']))
    indices_text = (
        "NDVI = (B8−B4)/(B8+B4); "
        "NDWI = (B3−B8)/(B3+B8); "
        "MNDWI = (B3−B11)/(B3+B11); "
        "NDBI = (B11−B8)/(B11+B8)."
    )
    story.append(Paragraph(indices_text, styles['BodyText2']))

    story.append(Paragraph("Classification", styles['SubsectionHeader']))
    if analysis.classifier == 'spectral':
        thresholds = analysis.thresholds
        class_text = (
            f"Spectral rule-based classification with thresholds: "
            f"Water (MNDWI > {thresholds['mndwi_water']}, NDVI < {thresholds['ndvi_water_max']}); "
            f"Vegetation (NDVI ≥ {thresholds['ndvi_veg_min']}); "
            f"Built-up/Bare (NDBI > {thresholds['ndbi_built_min']}, NDVI < {thresholds['ndvi_built_max']}); "
            f"Other: remaining valid pixels."
        )
    else:
        class_text = (
            "Google Dynamic World (GOOGLE/DYNAMICWORLD/V1) mode of label band over seasonal window. "
            "Classes remapped: water, trees/grass/crops/shrub→vegetation, built/bare→built-up, snow→other."
        )
    story.append(Paragraph(class_text, styles['BodyText2']))

    story.append(Paragraph("Area Calculation", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Pixel area from ee.Image.pixelArea() in km². Percentages use valid (unmasked) area as denominator. "
        "Raw district area also reported.",
        styles['BodyText2']
    ))

    story.append(PageBreak())

    # =========================================================================
    # RESULTS: YEARLY STATISTICS TABLE
    # =========================================================================
    story.append(Paragraph("Yearly Statistics", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['primary']))
    story.append(Spacer(1, 0.3*cm))

    # Build table
    table_data = [[
        Paragraph('Year', styles['TableHeader']),
        Paragraph('Images', styles['TableHeader']),
        Paragraph('Valid\nkm²', styles['TableHeader']),
        Paragraph('Veg\nkm²', styles['TableHeader']),
        Paragraph('Veg\n%', styles['TableHeader']),
        Paragraph('Water\nkm²', styles['TableHeader']),
        Paragraph('Water\n%', styles['TableHeader']),
        Paragraph('Built\nkm²', styles['TableHeader']),
        Paragraph('Built\n%', styles['TableHeader']),
        Paragraph('NDVI', styles['TableHeader']),
        Paragraph('MNDWI', styles['TableHeader']),
        Paragraph('NDBI', styles['TableHeader']),
        Paragraph('Quality', styles['TableHeader']),
    ]]

    for stat in analysis.stats:
        q = stat.quality
        flags = []
        if q.low_image_count: flags.append('⚠ Low images')
        if q.low_coverage: flags.append('⚠ Low coverage')
        if q.outlier_flag: flags.append('⚠ Outlier')
        quality_str = ', '.join(flags) if flags else 'OK'

        row = [
            Paragraph(str(stat.year), styles['TableCell']),
            Paragraph(str(stat.images_used), styles['TableCell']),
            Paragraph(f"{stat.valid_km2:.1f}", styles['TableCell']),
            Paragraph(f"{stat.vegetation_km2:.1f}", styles['TableCell']),
            Paragraph(f"{stat.vegetation_pct:.1f}", styles['TableCell']),
            Paragraph(f"{stat.water_km2:.1f}", styles['TableCell']),
            Paragraph(f"{stat.water_pct:.1f}", styles['TableCell']),
            Paragraph(f"{stat.built_bare_km2:.1f}", styles['TableCell']),
            Paragraph(f"{stat.built_bare_pct:.1f}", styles['TableCell']),
            Paragraph(f"{stat.mean_ndvi:.3f}", styles['TableCell']),
            Paragraph(f"{stat.mean_mndwi:.3f}", styles['TableCell']),
            Paragraph(f"{stat.mean_ndbi:.3f}", styles['TableCell']),
            Paragraph(quality_str, styles['TableCell']),
        ]
        table_data.append(row)

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, COLORS['bg_light']]),
    ]))

    story.append(table)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Table 1: Yearly land cover statistics. Quality flags indicate low image count (<5), "
        "low coverage (<50%), or outlier years (>25% difference from neighbor average).",
        styles['Caption']
    ))

    story.append(PageBreak())

    # =========================================================================
    # CHANGE SUMMARY TABLE
    # =========================================================================
    if len(analysis.stats) >= 2:
        story.append(Paragraph("Change Summary (First vs Last Year)", styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS['primary']))
        story.append(Spacer(1, 0.3*cm))

        first = analysis.stats[0]
        last = analysis.stats[-1]

        change_data = [[
            Paragraph('Class', styles['TableHeader']),
            Paragraph(f'{first.year} km²', styles['TableHeader']),
            Paragraph(f'{last.year} km²', styles['TableHeader']),
            Paragraph('Change km²', styles['TableHeader']),
            Paragraph('Change %', styles['TableHeader']),
        ]]

        for cls, label in [('vegetation', 'Vegetation'), ('water', 'Water'), ('built_bare', 'Built-up/Bare')]:
            v1 = getattr(first, f'{cls}_km2')
            v2 = getattr(last, f'{cls}_km2')
            change = v2 - v1
            pct = (change / v1 * 100) if v1 > 0 else 0
            change_data.append([
                Paragraph(label, styles['TableCell']),
                Paragraph(f"{v1:.2f}", styles['TableCell']),
                Paragraph(f"{v2:.2f}", styles['TableCell']),
                Paragraph(f"{change:+.2f}", styles['TableCell']),
                Paragraph(f"{pct:+.1f}%", styles['TableCell']),
            ])

        # NDVI row
        ndvi_change = last.mean_ndvi - first.mean_ndvi
        change_data.append([
            Paragraph('Mean NDVI', styles['TableCell']),
            Paragraph(f"{first.mean_ndvi:.3f}", styles['TableCell']),
            Paragraph(f"{last.mean_ndvi:.3f}", styles['TableCell']),
            Paragraph(f"{ndvi_change:+.3f}", styles['TableCell']),
            Paragraph("—", styles['TableCell']),
        ])

        change_table = Table(change_data)
        change_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, COLORS['bg_light']]),
        ]))
        story.append(change_table)
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            "Table 2: Net change between first and last analysis year. Positive values indicate gain.",
            styles['Caption']
        ))

    story.append(PageBreak())

    # =========================================================================
    # QUALITY ASSESSMENT
    # =========================================================================
    story.append(Paragraph("Data Quality Assessment", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['primary']))
    story.append(Spacer(1, 0.3*cm))

    quality = analysis.quality_summary
    story.append(Paragraph(
        f"<b>Years with warnings:</b> {quality.get('years_with_warnings', 0)}",
        styles['BodyText2']
    ))
    story.append(Paragraph(
        f"<b>Outlier years:</b> {', '.join(map(str, quality.get('outlier_years', []))) or 'None'}",
        styles['BodyText2']
    ))
    story.append(Paragraph(
        f"<b>Recommended baseline year:</b> {quality.get('best_quality_year', 'N/A')}",
        styles['BodyText2']
    ))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "Quality flags are computed per year: <b>Low images</b> (<5 images in composite), "
        "<b>Low coverage</b> (<50% valid pixels), <b>Outlier</b> (>25% deviation from "
        "neighbor-year average). Years flagged as outliers may produce artifactual jumps.",
        styles['BodyText2']
    ))

    # Per-year quality table
    q_data = [[
        Paragraph('Year', styles['TableHeader']),
        Paragraph('Images', styles['TableHeader']),
        Paragraph('Coverage %', styles['TableHeader']),
        Paragraph('Flags', styles['TableHeader']),
    ]]
    for stat in analysis.stats:
        q = stat.quality
        flags = []
        if q.low_image_count: flags.append('Low images')
        if q.low_coverage: flags.append('Low coverage')
        if q.outlier_flag: flags.append('Outlier')
        q_data.append([
            Paragraph(str(stat.year), styles['TableCell']),
            Paragraph(str(stat.images_used), styles['TableCell']),
            Paragraph(f"{q.valid_coverage_pct:.1f}", styles['TableCell']),
            Paragraph(', '.join(flags) if flags else 'OK', styles['TableCell']),
        ])

    q_table = Table(q_data)
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, COLORS['bg_light']]),
    ]))
    story.append(Spacer(1, 0.3*cm))
    story.append(q_table)

    story.append(PageBreak())

    # =========================================================================
    # CAVEATS & LIMITATIONS
    # =========================================================================
    story.append(Paragraph("Caveats and Limitations", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['primary']))
    story.append(Spacer(1, 0.3*cm))

    caveats = [
        "2018 data may have lower image count due to Sentinel-2 coverage limitations over India.",
        "Spectral 'built-up' class includes bare soil and fallow fields; use Dynamic World for comparison.",
        "Single seasonal window (Oct–Dec) mixes post-monsoon water and crop residue effects.",
        "District boundaries include large rural areas, diluting urban change signal.",
        f"Trend analysis with n={len(analysis.stats)} has very low statistical power; interpret cautiously.",
        "WorldCover validation only available for 2020 (v100) and 2021 (v200).",
        "Cloud mask may miss thin cirrus or over-mask bright surfaces.",
        "20 m analysis scale misses fine-grained features; 10 m option available.",
        "Dynamic World temporal resolution may miss sub-annual dynamics.",
        "All thresholds are adjustable; results are sensitive to threshold choices.",
    ]

    for i, caveat in enumerate(caveats, 1):
        story.append(Paragraph(f"{i}. {caveat}", styles['BodyText2']))

    story.append(PageBreak())

    # =========================================================================
    # RUN METADATA
    # =========================================================================
    story.append(Paragraph("Run Metadata", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['primary']))
    story.append(Spacer(1, 0.3*cm))

    meta = analysis.run_metadata
    meta_items = [
        ("Run date", meta.get('run_date', 'N/A')),
        ("GEE Project", meta.get('gee_project', 'N/A')),
        ("Sentinel Collection", meta.get('sentinel_collection', 'N/A')),
        ("Dynamic World Collection", meta.get('dynamic_world_collection', 'N/A')),
        ("Scale (m)", str(meta.get('scale_m', 'N/A'))),
        ("CRS", meta.get('crs', 'N/A')),
        ("Cloud Threshold", f"{meta.get('cloud_threshold', 'N/A')}%"),
        ("Classifier", meta.get('classifier', 'N/A')),
        ("Season", meta.get('season', {}).get('name', 'N/A')),
        ("District", meta.get('district', 'N/A')),
    ]

    meta_data = [[Paragraph('Parameter', styles['TableHeader']), Paragraph('Value', styles['TableHeader'])]]
    for k, v in meta_items:
        meta_data.append([Paragraph(k, styles['TableCell']), Paragraph(str(v), styles['TableCell'])])

    meta_table = Table(meta_data, colWidths=[6*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, COLORS['bg_light']]),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        REPORT_FOOTER_TEXT.format(date=datetime.utcnow().strftime('%Y-%m-%d')),
        styles['SmallText']
    ))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


async def generate_report(request: ReportRequest) -> Dict[str, Any]:
    """Generate PDF report for the given request."""
    # Run analysis using gee_processor directly (avoid circular import with main)
    from gee_processor import run_analysis as run_analysis_async

    analysis_request = type('obj', (object,), {
        'district_id': request.district_id,
        'geojson': request.geojson,
        'years': request.years,
        'season': request.season,
        'classifier': request.classifier,
        'thresholds': request.thresholds,
        'cloud_threshold': 80,
        'scale': 20,
        'baseline_year': request.baseline_year,
    })()

    analysis_result = await run_analysis_async(analysis_request)

    # Build report
    report_request_obj = type('obj', (object,), {
        'district_id': request.district_id,
        'years': request.years,
        'season': request.season,
        'cloud_threshold': 80,
    })()

    report_data = ReportData(
        analysis=type('obj', (object,), analysis_result)(),
        request=report_request_obj,
        charts={}
    )

    pdf_bytes = build_report(report_data)
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

    return {
        "pdf_base64": pdf_base64,
        "filename": f"UGBM_Report_{request.district_id or 'custom'}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    }