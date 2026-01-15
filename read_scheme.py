
import docx
import sys

def read_docx(file_path):
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"Error reading file: {e}"

if __name__ == "__main__":
    file_path = "行业分析报告中产业链自动抽取的多智能体协同方案.docx"
    with open("scheme_content.txt", "w", encoding="utf-8") as f:
        f.write(read_docx(file_path))
