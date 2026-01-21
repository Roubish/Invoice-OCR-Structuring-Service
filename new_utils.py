import pytesseract
import google.generativeai as genai
import json
import re
import cv2 as cv
from pdf2image import convert_from_path
import pdfplumber
import numpy as np
from pathlib import Path


# -------------------- AUTO ROTATION --------------------
def auto_rotate_image(img):
    """
    Rotate image if text orientation is vertical
    """
    try:
        osd = pytesseract.image_to_osd(img)
        angle = int(re.search(r"Rotate: (\d+)", osd).group(1))
    except Exception:
        angle = 0

    if angle != 0:
        h, w = img.shape[:2]
        M = cv.getRotationMatrix2D((w // 2, h // 2), -angle, 1.0)
        img = cv.warpAffine(img, M, (w, h))

    return img


# -------------------- IMAGE OCR --------------------
def extract_text_from_image(img):
    img = auto_rotate_image(img)
    return pytesseract.image_to_string(img, lang="eng")


# -------------------- TEXT PDF --------------------
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


# -------------------- SCANNED PDF --------------------
def pdf_to_images(pdf_path):
    pages = convert_from_path(pdf_path, dpi=300)
    return [cv.cvtColor(np.array(p), cv.COLOR_RGB2BGR) for p in pages]


# -------------------- STANDARDIZED ENTRY --------------------
def extract_text_from_file(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix in [".png", ".jpg", ".jpeg"]:
        img = cv.imread(file_path)
        if img is None:
            raise ValueError("Failed to read image")
        return extract_text_from_image(img)

    elif suffix == ".pdf":
        text = extract_text_from_pdf(file_path)
        if text:
            return text

        images = pdf_to_images(file_path)
        extracted = [extract_text_from_image(img) for img in images]
        return "\n".join(extracted)

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


# -------------------- HORIZONTAL TABLE EXTRACTION --------------------
def extract_line_items_from_text(text: str):
    items = []

    for line in text.splitlines():
        line = line.strip()

        match = re.search(
            r"^\d+\s+(.+?)\s+\d{2}/\d{2}/\d{4}\s+(\d+)\s+([\d.]+)\s+([\d.]+)",
            line
        )

        if match:
            items.append({
                "item_name": match.group(1).strip(),
                "item_quantity": float(match.group(2)),
                "item_rate": float(match.group(3)),
                "item_amount": float(match.group(4)),
            })

    return items


# -------------------- VERTICAL TABLE EXTRACTION --------------------
def extract_vertical_table(text: str):
    items, qtys, amounts = [], [], []

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines:
        if re.fullmatch(r"\d+", line):
            qtys.append(float(line))
        elif re.fullmatch(r"\d+\.\d{2}", line):
            amounts.append(float(line))
        elif len(line) > 4 and not re.search(r"\d{2}/\d{2}/\d{4}", line):
            items.append(line)

    count = min(len(items), len(qtys), len(amounts))

    return [
        {
            "item_name": items[i],
            "item_quantity": qtys[i],
            "item_amount": amounts[i]
        }
        for i in range(count)
    ]

def extract_items_loose(text: str):
    """
    Extract items even when layout is broken or vertical
    """
    items = []

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    current = {}

    for line in lines:
        # Item name (medicine names)
        if re.search(r"(tab|cap|syp|inj|mg|ml)", line.lower()):
            if current:
                items.append(current)
                current = {}
            current["item_name"] = line

        # Quantity
        elif re.fullmatch(r"\d+", line):
            current.setdefault("item_quantity", float(line))

        # Rate / Amount
        elif re.fullmatch(r"\d+\.\d{2}", line):
            if "item_rate" not in current:
                current["item_rate"] = float(line)
            else:
                current["item_amount"] = float(line)

    if current:
        items.append(current)

    # Keep only valid items
    valid_items = [
        i for i in items
        if "item_name" in i and "item_quantity" in i and "item_amount" in i
    ]

    return valid_items

# -------------------- GEMINI STRUCTURING --------------------
def structure_with_gemini(extracted_text, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Return a SINGLE JSON OBJECT (not an array).

    Extract all line items with:
    item_name, item_quantity, item_rate, item_amount

    Invoice text:
    ---
    {extracted_text}
    ---
    """

    return model.generate_content(prompt)


# -------------------- RESPONSE FORMATTER --------------------
def format_response(response):
    raw = response.candidates[0].content.parts[0].text
    cleaned = re.sub(r"```json|```", "", raw, flags=re.I).strip()
    parsed = json.loads(cleaned)

    if isinstance(parsed, list):
        parsed = parsed[0]

    if hasattr(response, "usage_metadata"):
        parsed.setdefault("data", {})
        parsed["data"]["token_usage"] = {
            "input_tokens": response.usage_metadata.prompt_token_count,
            "output_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count,
        }

    return parsed
