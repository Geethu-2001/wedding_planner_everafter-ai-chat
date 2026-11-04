from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from sqlalchemy import func
from wedding_planner.config import settings
from wedding_planner.models import Wedding, WeddingDocument, WeddingService, Vendor, Expense, WeddingTask
from wedding_planner.repositories import require_membership


def _p(value, style):
    text = str(value or "Not provided").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text, style)


def generate_wedding_pdf(session, wedding_id, user_id):
    require_membership(session, wedding_id, user_id)
    wedding = session.get(Wedding, wedding_id)
    if not wedding:
        raise ValueError("Wedding project not found.")
    version = (session.query(func.max(WeddingDocument.version))
               .filter_by(wedding_id=wedding_id).scalar() or 0) + 1
    folder = Path(settings.generated_dir) / f"wedding_{wedding_id}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"wedding_plan_v{version}.pdf"
    styles = getSampleStyleSheet()
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=10)
    story = [
        Paragraph("EverAfter AI — Wedding Plan", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Wedding profile", styles["Heading2"]),
        Table([
            ["Bride", wedding.bride_name or "TBD"],
            ["Groom", wedding.groom_name or "TBD"],
            ["Date", str(wedding.wedding_date or "TBD")],
            ["Location", ", ".join(x for x in [wedding.city, wedding.state, wedding.country] if x)],
            ["Guests", str(wedding.guest_count)],
            ["Style / type", f"{wedding.wedding_style} / {wedding.wedding_type}"],
            ["Total budget (INR)", f"{wedding.total_budget:,.2f}"],
        ], colWidths=[130, 360]),
        Spacer(1, 14),
        Paragraph("Selected providers", styles["Heading2"]),
    ]
    selected = session.query(Vendor).filter(
        Vendor.wedding_id == wedding_id,
        Vendor.selection_status.in_(["selected", "quotation_received", "booked"]),
    ).order_by(Vendor.category, Vendor.name).all()
    if selected:
        data = [["Category", "Provider", "Status", "Quotation (INR)"]]
        for vendor in selected:
            data.append([vendor.category, _p(vendor.name, small), vendor.selection_status.replace("_", " ").title(),
                         f"{vendor.quoted_amount:,.2f}" if vendor.quoted_amount is not None else "Not received"])
        table = Table(data, repeatRows=1, colWidths=[100, 190, 100, 100])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6b3e42")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8c7bd")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        for vendor in selected:
            story += [
                Spacer(1, 5),
                _p(f"<b>{vendor.category} — {vendor.name}</b>", small),
                _p(f"Price information: {vendor.price_text}", small),
                _p(f"Package: {vendor.package_details}", small),
                _p(f"Contact: {vendor.contact_details}", small),
                _p(f"Notes: {vendor.notes}", small),
                _p(f"Source: {vendor.source_url}", small),
            ]
    else:
        story.append(Paragraph("No providers have been selected yet.", styles["BodyText"]))

    shortlisted = session.query(Vendor).filter(
        Vendor.wedding_id == wedding_id, Vendor.selection_status == "shortlisted"
    ).order_by(Vendor.category, Vendor.name).all()
    if shortlisted:
        story += [Spacer(1, 12), Paragraph("Shortlisted — not yet selected", styles["Heading2"])]
        for vendor in shortlisted:
            story.append(_p(f"{vendor.category}: {vendor.name} — {vendor.price_text}", small))

    for title, model in [("Requested services", WeddingService), ("Expenses", Expense), ("Checklist", WeddingTask)]:
        story += [Spacer(1, 12), Paragraph(title, styles["Heading2"])]
        rows = session.query(model).filter_by(wedding_id=wedding_id).all()
        if not rows:
            story.append(Paragraph("None recorded.", styles["BodyText"]))
        for row in rows:
            if model is WeddingService:
                line = f"{row.category} · {row.requirements} · {row.status}"
            elif model is Expense:
                line = f"{row.category} · {row.description} · INR {row.amount} · {row.expense_type}"
            else:
                line = f"{row.title} · due {row.due_date or 'TBD'} · {row.status}"
            story.append(_p(line, small))

    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=42, leftMargin=42).build(story)
    session.add(WeddingDocument(wedding_id=wedding_id, file_path=str(path), version=version))
    session.commit()
    return path, version
