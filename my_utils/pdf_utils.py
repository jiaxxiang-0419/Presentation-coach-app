import fitz  # PyMuPDF
from PIL import Image
import streamlit as st

@st.cache_data(show_spinner=False)
def get_pdf_page_image(pdf_bytes, page_num):
    """PDFの指定ページを画像に変換する"""
    if not pdf_bytes:
        return None
        
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            return None
            
        # 💡 【絶対安全装置】ページ数がオーバーしてエラーになるのを強制的に防ぐ
        if page_num >= len(doc):
            page_num = len(doc) - 1
        elif page_num < 0:
            page_num = 0
            
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    except Exception as e:
        print(f"PDF Error: {e}")
        return None