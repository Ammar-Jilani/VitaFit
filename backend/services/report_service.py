# backend/services/report_service.py
import io
import datetime
from typing import Any, Dict, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from models.request_models import ReportRequest, UserPersonalDetails
from database.mongodb_client import get_db_collection
from utils.helpers import convert_numpy_types

async def generate_report(report_request: ReportRequest) -> StreamingResponse:
    """
    Generates a PDF report based on stored session predictions and user details.
    """
    try:
        predictions_collection = get_db_collection("predictions")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    prediction_record = predictions_collection.find_one({"session_id": report_request.session_id})

    if not prediction_record:
        raise HTTPException(status_code=404, detail=f"No predictions found for session ID: {report_request.session_id}")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    
    styles = getSampleStyleSheet()

    # Define custom styles
    styles.add(ParagraphStyle(name='ReportTitle',
                              fontSize=24,
                              leading=28,
                              alignment=1,
                              spaceAfter=20,
                              fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionHeader',
                              fontSize=16,
                              leading=18,
                              spaceBefore=10,
                              spaceAfter=8,
                              fontName='Helvetica-Bold',
                              textColor=colors.darkblue))
    styles.add(ParagraphStyle(name='SubSectionHeader',
                              fontSize=14,
                              leading=16,
                              spaceBefore=8,
                              spaceAfter=6,
                              fontName='Helvetica-BoldOblique',
                              textColor=colors.dimgray))
    styles.add(ParagraphStyle(name='NormalText',
                              fontSize=10,
                              leading=12,
                              spaceAfter=5,
                              fontName='Helvetica'))
    styles.add(ParagraphStyle(name='TableCaption',
                              fontSize=10,
                              leading=12,
                              spaceAfter=5,
                              alignment=1,
                              fontName='Helvetica-Bold'))

    elements = []

    # Title
    elements.append(Paragraph("Fitness and Diet Plan Report", styles['ReportTitle']))
    elements.append(Spacer(1, 0.3 * inch))

    # User Details
    if report_request.user_details and any(report_request.user_details.dict().values()):
        elements.append(Paragraph("User Personal Details", styles['SectionHeader']))
        user_data = []
        if report_request.user_details.first_name: user_data.append(["First Name:", report_request.user_details.first_name])
        if report_request.user_details.last_name: user_data.append(["Last Name:", report_request.user_details.last_name])
        if report_request.user_details.email: user_data.append(["Email:", report_request.user_details.email])
        if report_request.user_details.phone: user_data.append(["Phone:", report_request.user_details.phone])
        
        if user_data:
            table_style = TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#E8F5E9')),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#A5D6A7')),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ])
            elements.append(Table(user_data, style=table_style, colWidths=[2*inch, 4*inch]))
            elements.append(Spacer(1, 0.2 * inch))

    # Submitted Data
    elements.append(Paragraph("Submitted Input Data", styles['SectionHeader']))
    raw_input_data_for_report = []
    raw_user_input_stored = prediction_record.get('raw_user_input', {})
    for key, value in raw_user_input_stored.items():
        if value is not None and value != '' and key not in ['medical_conditions', 'dietary_restrictions', 'food_preferences']:
            raw_input_data_for_report.append([key.replace('_', ' ').title() + ":", str(value)])
    
    if raw_user_input_stored.get('medical_conditions'):
        raw_input_data_for_report.append(["Medical Conditions:", raw_user_input_stored['medical_conditions']])
    if raw_user_input_stored.get('dietary_restrictions'):
        raw_input_data_for_report.append(["Dietary Restrictions:", raw_user_input_stored['dietary_restrictions']])
    if raw_user_input_stored.get('food_preferences'):
        raw_input_data_for_report.append(["Food Preferences:", raw_user_input_stored['food_preferences']])

    if raw_input_data_for_report:
        elements.append(Table(raw_input_data_for_report, style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#BDBDBD')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F5F5F5')),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]), colWidths=[2*inch, 4*inch]))
        elements.append(Spacer(1, 0.2 * inch))

    # Exercise Plan
    elements.append(Paragraph("Generated Exercise Plan", styles['SectionHeader']))
    exercise_data = []
    for key, value in prediction_record.get('exercise_predictions', {}).items():
        exercise_data.append([key.replace('_', ' ').title() + ":", str(value)])
    if exercise_data:
        elements.append(Table(exercise_data, style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#81C784')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#C8E6C9')),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]), colWidths=[2.5*inch, 3.5*inch]))
        elements.append(Spacer(1, 0.2 * inch))

    # Diet Plan
    diet_predictions_data = prediction_record.get('diet_predictions', {})
    if diet_predictions_data and not (isinstance(diet_predictions_data, dict) and 'error' in diet_predictions_data):
        elements.append(Paragraph("Generated Diet Plan", styles['SectionHeader']))
        diet_data = []
        for key, value in diet_predictions_data.items():
            if key != "message":
                diet_data.append([key.replace('_', ' ').title() + ":", str(value)])
        if diet_data:
            elements.append(Table(diet_data, style=TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#64B5F6')),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#BBDEFB')),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]), colWidths=[2.5*inch, 3.5*inch]))
            elements.append(Spacer(1, 0.2 * inch))
    elif diet_predictions_data and "error" in diet_predictions_data:
        elements.append(Paragraph("Diet Plan Status:", styles['SectionHeader']))
        elements.append(Paragraph(f"Error: {diet_predictions_data['error']}", styles['NormalText']))
        elements.append(Spacer(1, 0.2 * inch))
    else:
        elements.append(Paragraph("Diet Plan Status:", styles['SectionHeader']))
        elements.append(Paragraph("Diet plan has not yet been generated for this session. Please use the /predict_diet endpoint first.", styles['NormalText']))
        elements.append(Spacer(1, 0.2 * inch))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    filename = f"Fitness_Report_{report_request.session_id}_{datetime.date.today()}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})