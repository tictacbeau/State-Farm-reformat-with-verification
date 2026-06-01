import os
import re
import threading
import io
import time
from datetime import datetime
import glob

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

import pdfplumber
from pypdf import PdfWriter, PdfReader

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# --- Configuration & Constants ---
APP_WIDTH = 620
APP_HEIGHT = 580

# UI Colors
BG_COLOR = "#F9FAFB"
BORDER_COLOR = "#E5E7EB"
TEXT_PRIMARY = "#111827"
TEXT_MUTED = "#6B7280"
PRIMARY_BLUE = "#2563EB"
HOVER_BLUE = "#1D4ED8"
DISABLED_BLUE = "#93C5FD"
SUCCESS_GREEN = "#16A34A"
ERROR_RED = "#DC2626"
LOG_BG = "#0F172A"
LOG_TEXT = "#94A3B8"
LOG_SUCCESS = "#4ADE80"
LOG_ERROR = "#F87171"

# ReportLab Colors
SF_RED = colors.HexColor("#CC0000")
DARK_GRAY = colors.HexColor("#222222")
MID_GRAY = colors.HexColor("#555555")
LIGHT_BG = colors.HexColor("#F5F5F5")
BORDER = colors.HexColor("#CCCCCC")
TBL_HDR = colors.HexColor("#444444")
ALT_ROW = colors.HexColor("#F0F0F0")
STAMP_BLUE = colors.HexColor("#003399")
WHITE = colors.HexColor("#FFFFFF")

# --- Helper Functions ---
def normalize_amount(raw: str) -> str:
    raw = str(raw).strip().lstrip('$')
    try:
        val = float(raw.replace(',', ''))
        return f'${val:,.2f}'
    except ValueError:
        return raw

def parse_float_amount(raw: str) -> float:
    raw = str(raw).strip().lstrip('$').replace(',', '')
    try:
        return float(raw)
    except ValueError:
        return 0.0

def total_from_filename(fname: str) -> float | None:
    base = os.path.basename(fname)
    base = re.sub(r'\s*\(\d+\).*', '', base)
    base = base.replace('.pdf', '').replace(',', '').lstrip('$')
    try:
        return float(base)
    except ValueError:
        return None

# --- PDF Generation ---
def create_payment_pdf(payment_data, invoices):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    elements = []
    
    # 1. "State Farm" in 7pt bold SF_RED, left-aligned
    style_sf = ParagraphStyle(
        name='StateFarm',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        textColor=SF_RED,
        leading=8
    )
    elements.append(Paragraph("State Farm", style_sf))
    elements.append(Spacer(1, 2))
    
    # 2. "Payment Details" in 18pt bold DARK_GRAY
    style_pd = ParagraphStyle(
        name='PaymentDetails',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=DARK_GRAY,
        leading=22
    )
    elements.append(Paragraph("Payment Details", style_pd))
    elements.append(Spacer(1, 6))
    
    # 3. Horizontal rule
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceBefore=0, spaceAfter=8))
    
    # 4. "Electronic funds transfer remittance information" in 10pt MID_GRAY
    style_eft = ParagraphStyle(
        name='EFT',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=MID_GRAY,
        leading=12
    )
    elements.append(Paragraph("Electronic funds transfer remittance information", style_eft))
    elements.append(Spacer(1, 15))
    
    # 5. RECEIVED Stamp Block
    style_stamp_1 = ParagraphStyle(
        name='Stamp1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13,
        textColor=STAMP_BLUE, alignment=TA_CENTER, leading=17
    )
    style_stamp_2 = ParagraphStyle(
        name='Stamp2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11,
        textColor=STAMP_BLUE, alignment=TA_CENTER, leading=15
    )
    style_stamp_3 = ParagraphStyle(
        name='Stamp3', parent=styles['Normal'], fontName='Helvetica', fontSize=8,
        textColor=STAMP_BLUE, alignment=TA_CENTER, leading=12
    )
    
    # Format date for stamp
    try:
        dt = datetime.strptime(payment_data.get('date', ''), "%m-%d-%Y")
        pay_date_stamp = dt.strftime("%b %d %Y").upper()
    except ValueError:
        pay_date_stamp = payment_data.get('date', '')
        
    elements.append(Paragraph("Received", style_stamp_1))
    elements.append(Paragraph(pay_date_stamp, style_stamp_2))
    elements.append(Paragraph("Acct Receivable Dept.", style_stamp_3))
    elements.append(Spacer(1, 20))
    
    # 6. Header info box
    left_col_text = ""
    if payment_data.get('firm_name'):
        left_col_text += f"<b>{payment_data['firm_name']}</b><br/>"
        if payment_data.get('firm_addr'):
            left_col_text += f"{payment_data['firm_addr']}<br/>"
        left_col_text += f"TIN: {payment_data.get('tin', '')}"
    elif payment_data.get('account_num'):
        left_col_text += f"<b>{payment_data['account_num']}</b><br/>"
        left_col_text += f"TIN: {payment_data.get('tin', '')}"
    else:
        left_col_text += f"TIN: {payment_data.get('tin', '')}"
        
    right_col_text = "<b>Payment information</b><br/>"
    right_col_text += f"Payment number: {payment_data.get('payment_num', '')}<br/>"
    right_col_text += f"Date: {payment_data.get('date', '')}"
    
    style_cell = ParagraphStyle(name='Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12)
    p_left = Paragraph(left_col_text, style_cell)
    p_right = Paragraph(right_col_text, style_cell)
    
    data_header = [[p_left, p_right]]
    # Adjust table width
    col_widths = [300, 240]
    t_header = Table(data_header, colWidths=col_widths)
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.75, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(t_header)
    elements.append(Spacer(1, 15))
    
    # 7. Invoice Table
    # Column widths: 72, 58, 108, 72, 100, 52, 44, 50
    inv_col_widths = [72, 58, 108, 72, 100, 52, 44, 50]
    
    # Ensure they fit the page
    style_th = ParagraphStyle(name='TH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, textColor=WHITE, alignment=TA_CENTER)
    style_td_l = ParagraphStyle(name='TDL', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9)
    style_td_r = ParagraphStyle(name='TDR', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9, alignment=TA_RIGHT)
    
    table_data = [[
        Paragraph("Billing Ref #", style_th),
        Paragraph("Inv. Date", style_th),
        Paragraph("Named Insured", style_th),
        Paragraph("Claim #", style_th),
        Paragraph("Contact", style_th),
        Paragraph("Submitted", style_th),
        Paragraph("Adjusted", style_th),
        Paragraph("Paid", style_th)
    ]]
    
    for inv in invoices:
        row = [
            Paragraph(inv.get('billing_ref', ''), style_td_l),
            Paragraph(inv.get('invoice_date', ''), style_td_l),
            Paragraph(inv.get('insured', ''), style_td_l),
            Paragraph(inv.get('claim_num', ''), style_td_l),
            Paragraph(inv.get('contact', ''), style_td_l),
            Paragraph(inv.get('submitted', ''), style_td_r),
            Paragraph(inv.get('adjusted', ''), style_td_r),
            Paragraph(inv.get('paid', ''), style_td_r),
        ]
        table_data.append(row)
        
    t_inv = Table(table_data, colWidths=inv_col_widths, repeatRows=1)
    
    # Style alternating rows
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), TBL_HDR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            ts.append(('BACKGROUND', (0, i), (-1, i), ALT_ROW))
        else:
            ts.append(('BACKGROUND', (0, i), (-1, i), WHITE))
            
    t_inv.setStyle(TableStyle(ts))
    elements.append(t_inv)
    elements.append(Spacer(1, 10))
    
    # 8. Thin horizontal rule
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=0, spaceAfter=6))
    
    # 9. Payment Total Line
    style_total = ParagraphStyle(name='Total', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, alignment=TA_RIGHT)
    total_str = f"Payment Total:   {payment_data.get('total_str', '')}"
    elements.append(Paragraph(total_str, style_total))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- GUI Application ---
class StateFarmFormatterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("State Farm EFT Formatter")
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)
        
        self.selected_folder = tk.StringVar()
        
        self.setup_ui()
        
        self.animation_running = False
        self.animation_alpha = 1.0
        self.animation_dir = -1
        
    def setup_ui(self):
        # Header Strip
        header_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=64)
        header_frame.pack(fill="x", side="top")
        
        # Border bottom for header
        header_border = ctk.CTkFrame(self, fg_color=BORDER_COLOR, corner_radius=0, height=1)
        header_border.pack(fill="x", side="top")
        
        # Logo square
        logo_canvas = tk.Canvas(header_frame, width=36, height=36, bg="#FFFFFF", highlightthickness=0)
        logo_canvas.place(x=24, y=14)
        self.round_rectangle(logo_canvas, 0, 0, 36, 36, radius=8, fill=SF_RED)
        logo_canvas.create_text(18, 18, text="SF", fill="#FFFFFF", font=("Segoe UI", 13, "bold"))
        
        # Titles
        title_label = ctk.CTkLabel(header_frame, text="State Farm EFT Formatter", text_color=TEXT_PRIMARY, font=("Segoe UI SemiBold", 15))
        title_label.place(x=70, y=10)
        
        subtitle_label = ctk.CTkLabel(header_frame, text="Remittance packet builder · Accounts Receivable", text_color=TEXT_MUTED, font=("Segoe UI", 12))
        subtitle_label.place(x=70, y=32)
        
        # Body
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=24, pady=20)
        
        # Input Folder Label
        input_label = ctk.CTkLabel(body_frame, text="INPUT FOLDER", text_color=TEXT_MUTED, font=("Segoe UI", 11, "bold"))
        input_label.pack(anchor="w")
        
        # Input Row
        input_row = ctk.CTkFrame(body_frame, fg_color="transparent")
        input_row.pack(fill="x", pady=(4, 0))
        
        self.entry_var = tk.StringVar(value="Select a folder containing State Farm EFT PDFs...")
        self.folder_entry = ctk.CTkEntry(
            input_row, 
            height=38, 
            corner_radius=8, 
            border_width=1.5,
            border_color=BORDER_COLOR,
            fg_color="#FFFFFF",
            text_color=TEXT_PRIMARY,
            font=("Consolas", 12),
            textvariable=self.entry_var,
            state="disabled"
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.browse_btn = ctk.CTkButton(
            input_row, 
            text="Browse…", 
            width=80, 
            height=38, 
            corner_radius=8,
            fg_color="#F9FAFB",
            border_width=1.5,
            border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY,
            hover_color="#F3F4F6",
            font=("Segoe UI", 13),
            command=self.browse_folder
        )
        self.browse_btn.pack(side="right")
        
        self.selected_path_label = ctk.CTkLabel(body_frame, text="", text_color=TEXT_MUTED, font=("Consolas", 11))
        self.selected_path_label.pack(anchor="w", pady=(4, 16))
        
        # Build Button
        self.build_btn = ctk.CTkButton(
            body_frame,
            text="Build Packet",
            height=42,
            corner_radius=9,
            fg_color=PRIMARY_BLUE,
            hover_color=HOVER_BLUE,
            text_color="#FFFFFF",
            font=("Segoe UI SemiBold", 14),
            command=self.start_processing
        )
        self.build_btn.pack(fill="x", pady=(0, 16))
        
        # Status Row
        status_row = ctk.CTkFrame(body_frame, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 16))
        
        self.status_canvas = tk.Canvas(status_row, width=16, height=16, bg=BG_COLOR, highlightthickness=0)
        self.status_canvas.pack(side="left", padx=(0, 6))
        self.status_circle = self.status_canvas.create_oval(3, 3, 13, 13, fill=TEXT_MUTED, outline="")
        
        self.status_label = ctk.CTkLabel(status_row, text="Select a folder to begin.", text_color=TEXT_MUTED, font=("Segoe UI Medium", 13))
        self.status_label.pack(side="left")
        
        # Progress Bar (Hidden initially)
        self.progress = ctk.CTkProgressBar(body_frame, height=8, corner_radius=99, fg_color="#EFF6FF", progress_color=PRIMARY_BLUE)
        self.progress.set(0)
        # Using place to hide/show, or just pack and unpack
        self.progress_frame = ctk.CTkFrame(body_frame, fg_color="transparent")
        
        self.progress.pack(in_=self.progress_frame, fill="x")
        self.pct_label = ctk.CTkLabel(self.progress_frame, text="0%", text_color=TEXT_MUTED, font=("Segoe UI", 12))
        self.pct_label.pack(side="right", pady=(2, 0))
        
        # Log Console
        self.log_console = ctk.CTkTextbox(
            body_frame,
            height=180,
            corner_radius=10,
            fg_color=LOG_BG,
            text_color=LOG_TEXT,
            font=("Consolas", 12),
            wrap="word",
            state="disabled"
        )
        self.log_console.pack(fill="x", pady=(16, 0))
        self.log_console.tag_config("success", foreground=LOG_SUCCESS)
        self.log_console.tag_config("error", foreground=LOG_ERROR)
        self.log_console.tag_config("info", foreground=LOG_TEXT)
        self.log_console.tag_config("warning", foreground="#FCD34D") # Yellow for warnings
        
        # Success Card (Hidden initially)
        self.success_card = ctk.CTkFrame(body_frame, fg_color="#F0FDF4", border_width=1, border_color="#BBF7D0", corner_radius=10)
        self.success_label = ctk.CTkLabel(self.success_card, text="✓ Packet created successfully", text_color=SUCCESS_GREEN, font=("Segoe UI SemiBold", 13))
        self.success_label.pack(pady=(12, 0))
        self.success_file_label = ctk.CTkLabel(self.success_card, text="", text_color=SUCCESS_GREEN, font=("Consolas", 12))
        self.success_file_label.pack(pady=(0, 6))
        self.open_btn = ctk.CTkButton(self.success_card, text="Open Folder ↗", height=28, fg_color=SUCCESS_GREEN, hover_color="#15803D", font=("Segoe UI", 12), command=self.open_output_folder)
        self.open_btn.pack(pady=(0, 12))
        
        # Footer Strip
        footer_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=36)
        footer_frame.pack(fill="x", side="bottom")
        
        footer_border = ctk.CTkFrame(self, fg_color=BORDER_COLOR, corner_radius=0, height=1)
        footer_border.place(x=0, y=self.winfo_height() - 36, relwidth=1) # Won't work with pack bottom
        
        footer_border2 = ctk.CTkFrame(footer_frame, fg_color=BORDER_COLOR, corner_radius=0, height=1)
        footer_border2.pack(fill="x", side="top")
        
        ctk.CTkLabel(footer_frame, text="Lewis Brisbois · Accounts Receivable", text_color=TEXT_MUTED, font=("Segoe UI", 11)).pack(side="left", padx=24, pady=6)
        ctk.CTkLabel(footer_frame, text="v1.0", text_color=TEXT_MUTED, font=("Segoe UI", 11)).pack(side="right", padx=24, pady=6)
        
    def round_rectangle(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_folder.set(folder)
            self.entry_var.set(folder)
            self.selected_path_label.configure(text=f"📁 {folder}")
            self.log_console.configure(state="normal")
            self.log_console.delete("1.0", "end")
            self.log_console.configure(state="disabled")
            self.success_card.pack_forget()
            self.progress_frame.pack_forget()
            self.set_status("Select a folder to begin.", TEXT_MUTED)
            self.log("Ready.", "info")

    def log(self, message, level="info"):
        self.log_console.configure(state="normal")
        self.log_console.insert("end", message + "\n", level)
        self.log_console.see("end")
        self.log_console.configure(state="disabled")

    def set_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)
        self.status_canvas.itemconfig(self.status_circle, fill=color)

    def pulse_animation(self):
        if not self.animation_running:
            self.status_canvas.itemconfig(self.status_circle, stipple="")
            return
            
        self.animation_alpha += self.animation_dir * 0.1
        if self.animation_alpha <= 0.3:
            self.animation_alpha = 0.3
            self.animation_dir = 1
        elif self.animation_alpha >= 1.0:
            self.animation_alpha = 1.0
            self.animation_dir = -1
            
        # Simulate opacity with stipple or just color blending
        # Tkinter canvas doesn't support alpha, so we blend color with BG
        r1, g1, b1 = self.winfo_rgb(PRIMARY_BLUE)
        r2, g2, b2 = self.winfo_rgb(BG_COLOR)
        r = int(r1 * self.animation_alpha + r2 * (1 - self.animation_alpha)) >> 8
        g = int(g1 * self.animation_alpha + g2 * (1 - self.animation_alpha)) >> 8
        b = int(b1 * self.animation_alpha + b2 * (1 - self.animation_alpha)) >> 8
        color = f"#{r:02x}{g:02x}{b:02x}"
        self.status_canvas.itemconfig(self.status_circle, fill=color)
        
        self.after(50, self.pulse_animation)

    def start_processing(self):
        folder = self.selected_folder.get()
        if not folder or not os.path.isdir(folder):
            self.log("Please select a valid input folder first.", "error")
            return
            
        self.build_btn.configure(state="disabled", text="Processing…", fg_color=DISABLED_BLUE)
        self.browse_btn.configure(state="disabled")
        
        self.success_card.pack_forget()
        self.progress_frame.pack(fill="x", pady=(0, 16), before=self.log_console)
        self.progress.set(0)
        self.progress.configure(progress_color=PRIMARY_BLUE)
        self.pct_label.configure(text="0%")
        
        self.set_status("Processing…", PRIMARY_BLUE)
        self.animation_running = True
        self.pulse_animation()
        
        self.log_console.configure(state="normal")
        self.log_console.delete("1.0", "end")
        self.log_console.configure(state="disabled")
        self.log(f"Starting processing in: {folder}", "info")
        
        thread = threading.Thread(target=self.process_pdfs, args=(folder,), daemon=True)
        thread.start()

    def process_pdfs(self, folder):
        try:
            pdf_files = glob.glob(os.path.join(folder, "*.pdf"))
            # Filter out existing merged packets if they exist to avoid re-processing
            pdf_files = [f for f in pdf_files if not os.path.basename(f).startswith("StateFarm_EFT_")]
            
            if not pdf_files:
                self.after(0, self.processing_complete, False, "No PDF files found in the folder.")
                return
                
            total_files = len(pdf_files)
            processed_buffers = []
            successful_files = 0
            skipped_files = 0
            
            for i, pdf_path in enumerate(pdf_files):
                filename = os.path.basename(pdf_path)
                result = self.parse_single_pdf(pdf_path)
                
                if result['status'] == 'failed':
                    skipped_files += 1
                    self.after(0, self.log, f"✗ SKIPPED: {filename} — {result['reason']}", "error")
                else:
                    successful_files += 1
                    # Warnings
                    for warn in result['warnings']:
                        self.after(0, self.log, f"⚠ {filename} — {warn}", "warning")
                        
                    # Create PDF buffer
                    buf = create_payment_pdf(result['payment_data'], result['invoices'])
                    processed_buffers.append({
                        'buffer': buf,
                        'total': result['payment_data']['total_numeric'],
                        'date': result['payment_data'].get('date', '')
                    })
                    
                    self.after(0, self.log, f"✓ Parsed: {filename} → {result['payment_data']['total_str']} ({len(result['invoices'])} invoices) [all checks passed]", "success")
                
                # Update progress
                pct = (i + 1) / total_files
                self.after(0, self.update_progress, pct)
                
            self.after(0, self.log, f"{successful_files} of {total_files} files parsed successfully. {skipped_files} skipped.", "info")
            
            if not processed_buffers:
                self.after(0, self.processing_complete, False, "No files were successfully processed.")
                return
                
            self.after(0, self.log, "Sorting pages by payment total...", "info")
            processed_buffers.sort(key=lambda x: x['total'], reverse=True)
            
            self.after(0, self.log, "Merging packets...", "info")
            merger = PdfWriter()
            for item in processed_buffers:
                reader = PdfReader(item['buffer'])
                merger.add_page(reader.pages[0])
                
            first_date = processed_buffers[0]['date']
            out_filename = f"StateFarm_EFT_{first_date}.pdf"
            out_path = os.path.join(folder, out_filename)
            
            with open(out_path, "wb") as f_out:
                merger.write(f_out)
                
            # Close buffers
            for item in processed_buffers:
                item['buffer'].close()
                
            self.after(0, self.processing_complete, True, out_path)
            
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self.after(0, self.processing_complete, False, f"An unexpected error occurred: {str(e)}")
            self.after(0, self.log, err, "error")

    def parse_single_pdf(self, pdf_path):
        lines = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if text:
                    for line in text.split('\n'):
                        stripped = line.strip()
                        if stripped:
                            lines.append(stripped)
                            
        full_text = "\n".join(lines)
        
        payment_data = {}
        invoices = []
        warnings = []
        
        # --- HEADER PARSING ---
        # Payment number
        m_pay_num = re.search(r'Payment\s+([A-Z0-9]{10,})', full_text)
        if m_pay_num:
            payment_data['payment_num'] = m_pay_num.group(1)
            
        # Payment date
        m_date = re.search(r'Date:\s*(\d{2}-\d{2}-\d{4})', full_text)
        if m_date:
            payment_data['date'] = m_date.group(1)
            
        # TIN
        m_tin = re.search(r'TIN:\s*(\*{4}\d{4})', full_text)
        if m_tin:
            payment_data['tin'] = m_tin.group(1)
            
        # Payment Total
        m_total = re.search(r'Payment Total:?\s*\$?([\d,]+\.?\d*)', full_text)
        if m_total:
            payment_data['total_str'] = normalize_amount(m_total.group(1))
            payment_data['total_numeric'] = parse_float_amount(m_total.group(1))
        else:
            payment_data['total_numeric'] = 0.0
            
        # Variant A vs Variant B Header
        firm_found = False
        if len(lines) > 2 and 'LEWIS BRISBOIS' in lines[2]:
            payment_data['firm_name'] = "Lewis Brisbois Bisgaard & Smith LLP"
            payment_data['firm_addr'] = "633 W 5th St Ste 4000, Los Angeles, CA 90071"
            firm_found = True
        else:
            # Variant A: Account number
            m_acc = re.search(r'^(\d{4,6}(?:-\d{3,4})?)\s+Payment information', full_text, re.MULTILINE)
            if m_acc:
                payment_data['account_num'] = m_acc.group(1)
                
        # --- INVOICE BLOCK PARSING ---
        billing_refs, invoice_dates, insureds, claim_nums = [], [], [], []
        contacts, submitted_l, adjusted_l, paid_l = [], [], [], []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line == 'Billing' and i+1 < len(lines) and lines[i+1].startswith('Reference '):
                billing_refs.append(lines[i+1][len('Reference '):].strip())
                i += 2
                continue
                
            if line == 'Number:' and i+1 < len(lines) and lines[i+1].startswith('Invoice date:'):
                m = re.match(r'Invoice date:\s*(\S+)', lines[i+1])
                invoice_dates.append(m.group(1) if m else '')
                i += 2
                continue
                
            if line == 'Named' and i+2 < len(lines) and lines[i+2] == 'insured:':
                insureds.append(lines[i+1])
                i += 3
                continue
                
            if line == 'Claim' and i+2 < len(lines) and lines[i+2] == 'number:':
                claim_nums.append(lines[i+1])
                i += 3
                continue
                
            if line == 'Contact' and i+2 < len(lines) and lines[i+2] == 'name:':
                contacts.append(lines[i+1])
                i += 3
                continue
                
            if line == 'Submitted' and i+2 < len(lines) and lines[i+2] == 'amount:':
                submitted_l.append(normalize_amount(lines[i+1]))
                i += 3
                continue
                
            if line == 'Adjusted' and i+2 < len(lines) and lines[i+2] == 'amount:':
                adjusted_l.append(normalize_amount(lines[i+1]))
                i += 3
                continue
                
            m = re.match(r'Paid amount:\s*(\S+)', line)
            if m:
                paid_l.append(normalize_amount(m.group(1)))
                i += 1
                continue
                
            i += 1
            
        # Compile invoices
        min_len = min(len(billing_refs), len(invoice_dates), len(insureds), len(claim_nums), 
                      len(contacts), len(submitted_l), len(adjusted_l), len(paid_l))
                      
        for j in range(min_len):
            invoices.append({
                'billing_ref': billing_refs[j],
                'invoice_date': invoice_dates[j],
                'insured': insureds[j],
                'claim_num': claim_nums[j],
                'contact': contacts[j],
                'submitted': submitted_l[j],
                'adjusted': adjusted_l[j],
                'paid': paid_l[j]
            })
            
        # --- VERIFICATION CHECKS ---
        
        # Check 1 - Billing ref is not a date (CRITICAL)
        for ref in billing_refs:
            if re.match(r'^\d{2}-\d{2}-\d{4}$', ref):
                return {'status': 'failed', 'reason': 'billing_ref looks like a date (parsing error)'}
                
        # Check 2 - Invoice field count consistency (WARNING)
        lengths = [len(billing_refs), len(invoice_dates), len(insureds), len(claim_nums), 
                   len(contacts), len(submitted_l), len(adjusted_l), len(paid_l)]
        if len(set(lengths)) > 1:
            warnings.append(f"field count mismatch: refs={lengths[0]} dates={lengths[1]} insureds={lengths[2]} claims={lengths[3]} contacts={lengths[4]} sub={lengths[5]} adj={lengths[6]} paid={lengths[7]}")
            
        # Check 3 - Payment total present (CRITICAL)
        if not m_total:
            return {'status': 'failed', 'reason': 'no payment total found'}
            
        # Check 4 - Total cross-check with filename (WARNING)
        file_total = total_from_filename(pdf_path)
        if file_total is not None and abs(file_total - payment_data['total_numeric']) > 0.02:
            warnings.append(f"total mismatch: parsed={payment_data['total_numeric']}, filename suggests={file_total}")
            
        # Check 5 - At least one invoice found (CRITICAL)
        if len(billing_refs) == 0:
            return {'status': 'failed', 'reason': 'no invoice blocks found'}
            
        return {
            'status': 'success',
            'payment_data': payment_data,
            'invoices': invoices,
            'warnings': warnings
        }

    def update_progress(self, pct):
        self.progress.set(pct)
        self.pct_label.configure(text=f"{int(pct*100)}%")

    def processing_complete(self, success, message_or_path):
        self.animation_running = False
        self.build_btn.configure(state="normal", text="Build Packet", fg_color=PRIMARY_BLUE)
        self.browse_btn.configure(state="normal")
        
        if success:
            self.set_status("Complete. Output saved to selected folder.", SUCCESS_GREEN)
            self.progress.configure(progress_color=SUCCESS_GREEN)
            
            # Show success card
            self.success_file_label.configure(text=os.path.basename(message_or_path))
            self.success_card.pack(fill="x", pady=(16, 0), before=self.log_console)
        else:
            self.set_status("An error occurred. Check the log.", ERROR_RED)
            if "An unexpected error occurred" in message_or_path or "No files" in message_or_path:
                self.log(message_or_path, "error")

    def open_output_folder(self):
        folder = self.selected_folder.get()
        if folder and os.path.exists(folder):
            os.startfile(folder)

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    app = StateFarmFormatterApp()
    app.mainloop()
