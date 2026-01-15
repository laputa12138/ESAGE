
import sys
import os

print(f"Python executable: {sys.executable}")

try:
    import pdfplumber
    print(f"pdfplumber version: {pdfplumber.__version__}")
    
    # Use a raw string for the path and forward slashes to avoid issues
    pdf_path = r"d:\工作\美国国防预算分析\ESAGE\data\20160707-万联证券-万联证券生物医药行业2016下半年投资策略报告：把握政策方向，寻找细分市场.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
    else:
        print(f"Testing PDF: {pdf_path}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > 0:
                    first_page = pdf.pages[0]
                    text = first_page.extract_text()
                    print("--- First Page Text Snippet ---")
                    print(text[:200] if text else "No text extracted")
                    print("-------------------------------")
                    print("Chinese PDF processed successfully.")
                else:
                    print("PDF has no pages.")
        except Exception as e:
            print(f"Error processing PDF with pdfplumber: {e}")

except ImportError as e:
    print(f"Failed to import pdfplumber: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
