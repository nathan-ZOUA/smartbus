from decimal import Decimal
from html import escape
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.bookings.models import Booking
from apps.core.permissions import user_has_role
from apps.payments.models import PaymentAttempt
from apps.sales.models import SaleOrder
from .models import ContractDocument


CONTRACT_ACCESS_ROLES = {
    "SUPER_ADMIN",
    "ADMIN",
    "FLEET_MANAGER",
    "SALES_AGENT",
}


def _money(value):
    return f"{Decimal(str(value)):,.0f}".replace(",", " ") + " XAF"


def _payment_reference(booking=None, sale_order=None):
    query = PaymentAttempt.objects.filter(
        status=PaymentAttempt.Status.VERIFIED,
    )
    if booking:
        query = query.filter(booking=booking)
    else:
        query = query.filter(sale_order=sale_order)
    return query.order_by("-reviewed_at").values_list(
        "transaction_reference", flat=True
    ).first()


def _snapshot(customer, bus, amount, kind, payment_reference, booking=None):
    full_name = " ".join(
        part.strip()
        for part in (customer.first_name, customer.last_name)
        if part and part.strip()
    )
    profile = getattr(customer, "profile", None)
    details = {
        "customer_username": customer.username,
        "customer_name": full_name or customer.username,
        "customer_email": customer.email or "",
        "customer_phone": profile.phone if profile else "",
        "agency_name": settings.SMARTBUS_LEGAL_NAME.strip(),
        "agency_address": settings.SMARTBUS_LEGAL_ADDRESS.strip(),
        "agency_phone": settings.SMARTBUS_LEGAL_PHONE.strip(),
        "agency_registration": settings.SMARTBUS_LEGAL_REGISTRATION.strip(),
        "registration": bus.registration,
        "vehicle": f"{bus.make} {bus.model} ({bus.year})",
        "amount": str(amount),
        "currency": "XAF",
        "payment_reference": payment_reference or "",
        "generated_at": timezone.localtime().strftime("%Y-%m-%d %H:%M"),
    }
    if kind == ContractDocument.Kind.RENTAL:
        details.update(
            {
                "start_date": booking.start_date.isoformat(),
                "end_date": booking.end_date.isoformat(),
                "destination": booking.destination,
                "passengers": booking.passengers,
            }
        )
    return details


def _paragraph(value, style):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _build_pdf(contract):
    snapshot = contract.snapshot
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SmartBusTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#15374b"),
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmartBusNotice",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#8d4315"),
            borderColor=colors.HexColor("#ead3a1"),
            borderWidth=0.7,
            borderPadding=8,
            backColor=colors.HexColor("#fff9ec"),
            spaceAfter=6 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmartBusSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#15374b"),
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmartBusSmall",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
            spaceAfter=2 * mm,
        )
    )

    title = (
        "PROJET DE CONTRAT DE LOCATION"
        if contract.kind == ContractDocument.Kind.RENTAL
        else "PROJET DE CONTRAT DE VENTE"
    )
    story = [
        Paragraph(title, styles["SmartBusTitle"]),
        _paragraph(
            f"Référence SmartBus : {contract.reference} — Émis le {snapshot['generated_at']}",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
        _paragraph(
            "BROUILLON NON SIGNÉ — Ce document est un récapitulatif généré par SmartBus. "
            "Il ne constitue pas un contrat complet ni un reçu Orange Money. "
            "Compléter les conditions manquantes et faire vérifier ce document par un "
            "professionnel du droit au Cameroun avant toute signature.",
            styles["SmartBusNotice"],
        ),
        Paragraph("PARTIES", styles["SmartBusSection"]),
        _paragraph(
            f"Agence : {snapshot['agency_name'] or '[nom légal à configurer]'}\n"
            f"Adresse de l'agence : {snapshot['agency_address'] or '[à compléter]'}\n"
            f"Identifiant légal / RCCM : {snapshot['agency_registration'] or '[à compléter]'}\n"
            f"Téléphone de l'agence : {snapshot['agency_phone'] or '[à compléter]'}\n"
            f"Client : {snapshot['customer_name']}\n"
            f"Identifiant client : {snapshot['customer_username']}\n"
            f"Courriel : {snapshot['customer_email'] or '[à compléter]'}\n"
            f"Téléphone : {snapshot['customer_phone'] or '[à compléter]'}",
            styles["SmartBusSmall"],
        ),
        Paragraph("VÉHICULE ET MONTANT", styles["SmartBusSection"]),
    ]
    vehicle_rows = [
        ["Véhicule", snapshot["vehicle"]],
        ["Immatriculation", snapshot["registration"]],
        ["Montant convenu (devise XAF)", _money(snapshot["amount"])],
        [
            "Référence Orange Money vérifiée",
            snapshot["payment_reference"] or "[à compléter]",
        ],
    ]
    if contract.kind == ContractDocument.Kind.RENTAL:
        vehicle_rows.extend(
            [
                ["Période de location", f"{snapshot['start_date']} au {snapshot['end_date']}"],
                ["Destination", snapshot["destination"]],
                ["Nombre de passagers", str(snapshot["passengers"])],
                ["Caution, remise et retour", "[à définir et à faire valider]"],
            ]
        )
    else:
        vehicle_rows.extend(
            [
                ["Objet", "Transfert du véhicule, à compléter selon les pièces requises"],
                ["État, kilométrage et remise des clés", "[à inspecter et à compléter]"],
                ["Documents de propriété et formalités", "[à compléter]"],
            ]
        )
    table = Table(
        [[_paragraph(label, styles["SmartBusSmall"]),
          _paragraph(value, styles["SmartBusSmall"])] for label, value in vehicle_rows],
        colWidths=[58 * mm, 112 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf3f6")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6e0e6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            table,
            Paragraph("CONDITIONS À COMPLÉTER AVANT SIGNATURE", styles["SmartBusSection"]),
            _paragraph(
                "Assurance et responsabilités · dépôt de garantie · état des lieux · "
                "retard et restitution · annulation et remboursement · pénalités éventuelles · "
                "entretien et réparations · taxes et frais · procédure de réclamation · "
                "loi applicable et juridiction compétente.",
                styles["SmartBusSmall"],
            ),
            Paragraph("SIGNATURES — après révision et accord des parties", styles["SmartBusSection"]),
            KeepTogether(
                [
                    _paragraph(
                        "Fait à : __________________________    Le : ____ / ____ / ______<br/><br/>"
                        "Pour l'agence : __________________________<br/><br/>"
                        "Le client : _________________________________<br/><br/>"
                        "Chaque partie confirme avoir lu et accepté la version finale "
                        "après complétion des conditions.",
                        styles["SmartBusSmall"],
                    ),
                ]
            ),
        ]
    )

    def add_page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6a7d8d"))
        canvas.drawString(20 * mm, 13 * mm, "SmartBus · Document brouillon non signé")
        canvas.drawRightString(190 * mm, 13 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"{title} {contract.reference}",
        author="SmartBus · Nathan Zoua",
    )
    document.build(story, onFirstPage=add_page_footer, onLaterPages=add_page_footer)
    return output.getvalue()


def contract_pdf_response(contract):
    pdf = _build_pdf(contract)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="smartbus-{contract.reference.lower()}.pdf"'
    )
    response["Cache-Control"] = "private, no-store"
    return response


def can_access_contract(user, customer):
    return user.pk == customer.pk or user_has_role(user, CONTRACT_ACCESS_ROLES)


def create_rental_contract(booking):
    reference = ContractDocument.make_reference(ContractDocument.Kind.RENTAL)
    snapshot = _snapshot(
        booking.customer,
        booking.bus,
        booking.total_price,
        ContractDocument.Kind.RENTAL,
        _payment_reference(booking=booking),
        booking=booking,
    )
    return ContractDocument.objects.get_or_create(
        booking=booking,
        defaults={
            "reference": reference,
            "kind": ContractDocument.Kind.RENTAL,
            "customer": booking.customer,
            "snapshot": snapshot,
        },
    )[0]


def create_sale_contract(sale_order):
    reference = ContractDocument.make_reference(ContractDocument.Kind.SALE)
    snapshot = _snapshot(
        sale_order.customer,
        sale_order.bus,
        sale_order.amount,
        ContractDocument.Kind.SALE,
        _payment_reference(sale_order=sale_order),
    )
    return ContractDocument.objects.get_or_create(
        sale_order=sale_order,
        defaults={
            "reference": reference,
            "kind": ContractDocument.Kind.SALE,
            "customer": sale_order.customer,
            "snapshot": snapshot,
        },
    )[0]


def can_generate_rental_contract(booking):
    return booking.status in {Booking.Status.PAID, Booking.Status.COMPLETED}


def can_generate_sale_contract(sale_order):
    return sale_order.status == SaleOrder.Status.PAID
