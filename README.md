# Invoice Intelligence – OCR & Line Item Extraction API

An end-to-end **Invoice OCR and Line Item Extraction system** built using **FastAPI, Tesseract OCR, OpenCV, and Google Gemini LLM**.  
This API automates invoice processing by extracting structured billing data from images and PDFs, reducing manual effort and human errors.

---

## Features

- Supports **Image & PDF invoices**
- Automatic **OCR text extraction**
- **Auto-rotation** for scanned documents
- Extracts invoice **line items**
  - Item Name
  - Quantity
  - Rate
  - Amount
- Handles **horizontal and vertical table layouts**
- **LLM fallback (Google Gemini)** for complex invoices
- REST API built with **FastAPI**
- Clean, structured JSON output

---

## Architecture Overview

1. **Input**  
   - Image (`.png`, `.jpg`, `.jpeg`)  
   - PDF (text-based or scanned)

2. **OCR Pipeline**
   - Image preprocessing & auto-rotation
   - Text extraction using Tesseract OCR
   - PDF text extraction using pdfplumber
   - OCR fallback for scanned PDFs

3. **Data Extraction**
   - Regex-based horizontal table parsing
   - Vertical / rotated table detection
   - Loose extraction for broken layouts

4. **LLM Fallback**
   - Google Gemini structures data when OCR parsing fails

5. **API Response**
   - Structured JSON with line items & totals

---

## Tech Stack

- **Backend**: FastAPI
- **OCR**: Tesseract OCR
- **Image Processing**: OpenCV
- **PDF Processing**: pdfplumber, pdf2image
- **LLM**: Google Gemini
- **Language**: Python

---

## Project Structure

```.
├── main.py # FastAPI entry point
├── new_utils.py # OCR & extraction utilities
├── requirements.txt
├── .env # API keys
└── README.md
```
---

## Environment Variables

Create a `.env` file:

```env
API_KEY=your_gemini_api_key
```
Running the Project
1️Install Dependencies
pip install -r requirements.txt

2️Start the API Server
uvicorn main:app --reload

3️API Health Check
GET /


Response:

{
  "message": "Invoice OCR API is running "
}

Extract Invoice Data
Endpoint
POST /extract

Request

Form-data

Key: file

Value: Invoice image or PDF

Sample Response
```{
  "is_success": true,
  "data": {
    "pagewise_line_items": [
      {
        "page_no": "1",
        "bill_items": [
          {
            "item_name": "Paracetamol 500mg",
            "item_quantity": 2,
            "item_rate": 25.0,
            "item_amount": 50.0
          }
        ]
      }
    ],
    "total_item_count": 1,
    "reconciled_amount": 50.0
  }
}
```
## Challenges Solved
- Handling rotated & scanned invoices
- Extracting data from non-standard layouts
- Reducing OCR noise using rule-based parsing
- Ensuring reliability with LLM-based fallback
