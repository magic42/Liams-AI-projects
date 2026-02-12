#!/usr/bin/env python3
"""Generate PDF for Rivet Tools Category Mapping"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime

# Output file
output_file = "rivet-tools-category-mapping.pdf"

# Create document
doc = SimpleDocTemplate(
    output_file,
    pagesize=A4,
    rightMargin=1.5*cm,
    leftMargin=1.5*cm,
    topMargin=1.5*cm,
    bottomMargin=1.5*cm
)

# Styles
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    spaceAfter=12,
    alignment=TA_CENTER
)
subtitle_style = ParagraphStyle(
    'CustomSubtitle',
    parent=styles['Normal'],
    fontSize=12,
    spaceAfter=20,
    alignment=TA_CENTER,
    textColor=colors.grey
)
heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=14,
    spaceBefore=20,
    spaceAfter=10,
    textColor=colors.HexColor('#333333')
)
subheading_style = ParagraphStyle(
    'CustomSubheading',
    parent=styles['Heading3'],
    fontSize=12,
    spaceBefore=15,
    spaceAfter=8,
    textColor=colors.HexColor('#555555')
)

# Table style
table_style = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('TOPPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9f9f9')),
    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ('TOPPADDING', (0, 1), (-1, -1), 6),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f5f5f5')]),
])

# Content
content = []

# Title
content.append(Paragraph("Rivet Tools Category Mapping", title_style))
content.append(Paragraph("www.part-on.co.uk", subtitle_style))
content.append(Spacer(1, 20))

# Main Category
content.append(Paragraph("Main Category", heading_style))
main_data = [
    ["Category", "URL"],
    ["Rivet Tools", "https://www.part-on.co.uk/category/rivet-tools-riveter/"]
]
main_table = Table(main_data, colWidths=[150, 350])
main_table.setStyle(table_style)
content.append(main_table)

# Level 1: Main Sections
content.append(Paragraph("Level 1: Main Sections", heading_style))
level1_data = [
    ["Section", "URL"],
    ["Rivet & Rivet Nut Tooling", "https://www.part-on.co.uk/category/rivet-and-rivet-nut-tooling/"],
    ["Fastening Tool Spares", "https://www.part-on.co.uk/category/spare-parts/"],
    ["Reconditioned Tools", "https://www.part-on.co.uk/category/reconditioned-tools/"],
    ["Manufactures", "https://www.part-on.co.uk/category/rivet-and-rivet-nut-tooling-brand/"],
    ["Tools By Fastener", "https://www.part-on.co.uk/category/tools-by-fastener/"],
]
level1_table = Table(level1_data, colWidths=[150, 350])
level1_table.setStyle(table_style)
content.append(level1_table)

# Level 2: Rivet & Rivet Nut Tooling
content.append(Paragraph("Level 2: Rivet & Rivet Nut Tooling (Children)", subheading_style))
tooling_data = [
    ["Category", "URL"],
    ["Rivet Air Tools", "https://www.part-on.co.uk/category/rivet-air-tools/"],
    ["Rivet Hand Tools", "https://www.part-on.co.uk/category/rivet-hand-tools/"],
    ["Rivet Nut Air Tools", "https://www.part-on.co.uk/category/rivet-nut-tools/"],
    ["Rivet Nut Hand Tools", "https://www.part-on.co.uk/category/rivet-nut-hand-tools/"],
    ["Structural Rivet Tools", "https://www.part-on.co.uk/category/structural-rivet-tools/"],
    ["Battery Rivet/Rivet Nut Tools", "https://www.part-on.co.uk/category/battery-rivetrivet-nut-tools/"],
    ["Automated Rivet / Rivet Nut Tools", "https://www.part-on.co.uk/category/automated-rivet-rivet-nut-tools/"],
    ["Discontinued Tooling", "https://www.part-on.co.uk/category/discontinued-tooling-pop-masterfix-avdel-gesipa-far-lobster/"],
]
tooling_table = Table(tooling_data, colWidths=[180, 320])
tooling_table.setStyle(table_style)
content.append(tooling_table)

# Level 2: Fastening Tool Spares
content.append(Paragraph("Level 2: Fastening Tool Spares (Children)", subheading_style))
spares_data = [
    ["Category", "URL"],
    ["Riveter Parts", "https://www.part-on.co.uk/category/riveter-parts/"],
    ["Rivet Nut Tool Parts", "https://www.part-on.co.uk/category/rivet-nut-tool-parts/"],
    ["Used Spare Parts", "https://www.part-on.co.uk/category/used-spare-parts/"],
]
spares_table = Table(spares_data, colWidths=[150, 350])
spares_table.setStyle(table_style)
content.append(spares_table)

# Level 2: Reconditioned Tools
content.append(Paragraph("Level 2: Reconditioned Tools (Children)", subheading_style))
recond_data = [
    ["Category", "URL"],
    ["Rivet Tools", "https://www.part-on.co.uk/category/reconditioned-rivet-tools/"],
    ["Rivet Nut Tools", "https://www.part-on.co.uk/category/reconditioned-rivet-nut-tools/"],
]
recond_table = Table(recond_data, colWidths=[150, 350])
recond_table.setStyle(table_style)
content.append(recond_table)

# Level 2: Manufactures
content.append(Paragraph("Level 2: Manufactures (Children)", subheading_style))
manu_data = [
    ["Category", "URL"],
    ["Avdel Tooling & Parts", "https://www.part-on.co.uk/category/avdel/"],
    ["FAR Tooling & Parts", "https://www.part-on.co.uk/category/far/"],
    ["Gesipa Tooling & Parts", "https://www.part-on.co.uk/category/gesipa/"],
    ["Lobster Tooling & Parts", "https://www.part-on.co.uk/category/lobster-tooling-spares/"],
    ["POP Tooling & Parts", "https://www.part-on.co.uk/category/pop/"],
    ["Masterfix Tooling & Parts", "https://www.part-on.co.uk/category/masterfix/"],
]
manu_table = Table(manu_data, colWidths=[150, 350])
manu_table.setStyle(table_style)
content.append(manu_table)

# Level 2: Tools By Fastener
content.append(Paragraph("Level 2: Tools By Fastener (Children)", subheading_style))
fastener_data = [
    ["Category", "URL"],
    ["Tools To Set POP Rivets", "https://www.part-on.co.uk/category/tools-to-set-standard-rivets/"],
    ["Tools To Set MONOBOLT", "https://www.part-on.co.uk/category/tools-to-set-monobolt-rivets/"],
    ["Tools To Set Tamp Rivets", "https://www.part-on.co.uk/category/tools-to-set-high-strength-rivets/"],
    ["Tools To Set Lockbolts", "https://www.part-on.co.uk/category/tools-to-set-lockbolts/"],
    ["Tools To Set Rivet Nuts", "https://www.part-on.co.uk/category/tools-to-set-rivet-nuts/"],
    ["Tools To Set Rivet Bolts", "https://www.part-on.co.uk/category/tools-to-set-rivet-bolts/"],
]
fastener_table = Table(fastener_data, colWidths=[150, 350])
fastener_table.setStyle(table_style)
content.append(fastener_table)

# Footer
content.append(Spacer(1, 30))
footer_style = ParagraphStyle(
    'Footer',
    parent=styles['Normal'],
    fontSize=8,
    textColor=colors.grey,
    alignment=TA_CENTER
)
content.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))

# Build PDF
doc.build(content)
print(f"PDF created: {output_file}")
