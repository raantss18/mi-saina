"""Extraction de texte de documents (services/documents.py)."""
import base64
import pytest

from services import documents


def test_txt(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("Bonjour le monde\nDeuxième ligne")
    text, err = documents.extract_text(str(f))
    assert err is None
    assert "Bonjour le monde" in text and "Deuxième ligne" in text


def test_csv(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("nom,age\nAlice,30\nBob,25")
    text, err = documents.extract_text(str(f))
    assert err is None and "Alice" in text and "age" in text


def test_missing_file():
    text, err = documents.extract_text("/n/existe/pas.pdf")
    assert text == "" and err and "introuvable" in err.lower()


def test_truncation(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("a" * 5000)
    text, err = documents.extract_text(str(f), max_chars=100)
    assert err is None and "tronqué" in text and len(text) < 300


def test_docx(tmp_path):
    docx = pytest.importorskip("docx")
    p = tmp_path / "doc.docx"
    d = docx.Document()
    d.add_paragraph("Paragraphe un")
    d.add_paragraph("Paragraphe deux")
    d.save(str(p))
    text, err = documents.extract_text(str(p))
    assert err is None and "Paragraphe un" in text and "Paragraphe deux" in text


def test_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    p = tmp_path / "sheet.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["produit", "prix"])
    ws.append(["pomme", 2])
    wb.save(str(p))
    text, err = documents.extract_text(str(p))
    assert err is None and "produit" in text and "pomme" in text


def test_extract_from_base64(tmp_path):
    raw = "Contenu en clair".encode()
    b64 = base64.b64encode(raw).decode()
    text, err = documents.extract_from_base64(b64, "fichier.txt")
    assert err is None and "Contenu en clair" in text


def test_pdf(tmp_path):
    # Génère un PDF minimal si reportlab est dispo, sinon on saute.
    rl = pytest.importorskip("reportlab.pdfgen.canvas")
    p = tmp_path / "doc.pdf"
    c = rl.Canvas(str(p))
    c.drawString(72, 720, "Texte du PDF")
    c.save()
    text, err = documents.extract_text(str(p))
    assert err is None and "Texte du PDF" in text
