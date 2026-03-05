from fastapi import APIRouter, UploadFile, File
import easyocr
import cv2
import numpy as np
from PIL import Image
import io
import re

router = APIRouter()

reader = easyocr.Reader(['de'], gpu=False)

# ---------------------------------------------------------
# NORMALISIERUNG: macht OCR-Ausgabe DB-kompatibel
# ---------------------------------------------------------
def normalize_ocr_value(s: str) -> str:
    if not s:
        return None

    s = s.lower().strip()

    # Entferne Leerzeichen und typische OCR-Artefakte
    remove_chars = [" ", "\n", "\t", "[", "]", "(", ")", "|"]
    for ch in remove_chars:
        s = s.replace(ch, "")

    # Typische OCR-Verwechslungen korrigieren
    ocr_fix = {
        "0": "o",   # 0 -> o
        "1": "i",   # 1 -> i
        "l": "i",   # l -> i
        "5": "s",   # 5 -> s
        "6": "g",   # 6 -> g
        "8": "b",   # 8 -> b
        "§": "s",
        "€": "e",
        "ß": "ss",
    }

    for wrong, right in ocr_fix.items():
        s = s.replace(wrong, right)

    # Doppelte Fehler korrigieren
    s = s.replace("g1", "gi")
    s = s.replace("i1", "ih")
    s = s.replace("1h", "ih")

    return s


# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------
def extract_first(pattern, text):
    if not text:
        return None
    m = re.search(pattern, text)
    return m.group(1) if m else None


def find_label_region(img):
    edges = cv2.Canny(img, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_area = 0

    for c in contours:
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            area = w * h
            if area > best_area:
                best_area = area
                best = (x, y, w, h)

    return best


# ---------------------------------------------------------
# OCR ENDPOINT
# ---------------------------------------------------------
@router.post("/ocr/etikett")
async def ocr_etikett(file: UploadFile = File(...)):
    content = await file.read()

    image = Image.open(io.BytesIO(content)).convert("L")
    img = np.array(image)

    region = find_label_region(img)

    if region:
        x, y, w, h = region
        crop = img[y:y+h, x:x+w]
    else:
        crop = img

    crop = cv2.GaussianBlur(crop, (3, 3), 0)
    crop = cv2.equalizeHist(crop)

    texts = reader.readtext(
        crop,
        detail=0,
        paragraph=False,
        contrast_ths=0.05,
        adjust_contrast=0.7,
        text_threshold=0.6,
        decoder='greedy'
    )

    full_text = " ".join(t for t in texts if t).replace("\n", " ")

    # ---------------------------------------------------------
    # REGEX + NORMALISIERUNG
    # ---------------------------------------------------------
    kuerzel_raw = extract_first(r"/\s*([A-Z0-9]{4,10})", full_text)
    stueckzahl_raw = extract_first(r"(\d+)\s*St\b", full_text)
    durchmesser_raw = extract_first(r"\b\d{1,2}/(\d{1,2})\b", full_text)
    laenge_raw = extract_first(r"L[: ]+(\d{2,4})\b", full_text)
    artikelnummer_raw = extract_first(r"([A-Z0-9]{3,10}-\d{6,10})", full_text)

    # Normalisieren
    kuerzel = normalize_ocr_value(kuerzel_raw)
    stueckzahl = normalize_ocr_value(stueckzahl_raw)
    durchmesser = normalize_ocr_value(durchmesser_raw)
    laenge = normalize_ocr_value(laenge_raw)
    artikelnummer = normalize_ocr_value(artikelnummer_raw)

    return {
        "kuerzel": kuerzel,
        "stueckzahl": stueckzahl,
        "durchmesser": durchmesser,
        "laenge": laenge,
        "artikelnummer": artikelnummer,
        "debug_raw": {
            "full_text": full_text,
            "region": region,
            "raw": {
                "kuerzel": kuerzel_raw,
                "stueckzahl": stueckzahl_raw,
                "durchmesser": durchmesser_raw,
                "laenge": laenge_raw,
                "artikelnummer": artikelnummer_raw
            }
        }
    }
