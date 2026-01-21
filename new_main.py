from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import Dict, Any
from dotenv import load_dotenv
import os
import tempfile
import new_utils

app = FastAPI()

load_dotenv()
api_key = os.getenv("API_KEY")


@app.get("/")
def home():
    return {"message": "Invoice OCR API is running 🚀"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        if not api_key:
            raise HTTPException(status_code=500, detail="API_KEY not found")

        contents = await file.read()
        suffix = os.path.splitext(file.filename)[-1]

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        extracted_text = new_utils.extract_text_from_file(temp_path)

        # 1️⃣ Horizontal table
        items = new_utils.extract_line_items_from_text(extracted_text)

        # 2️⃣ Vertical / rotated table
        if not items:
            items = new_utils.extract_vertical_table(extracted_text)

        # 3️⃣ If extracted → return immediately
        if items:
            return {
                "is_success": True,
                "data": {
                    "pagewise_line_items": [
                        {
                            "page_no": "1",
                            "bill_items": items
                        }
                    ],
                    "total_item_count": len(items),
                    "reconciled_amount": round(
                        sum(i.get("item_amount", 0) for i in items), 2
                    )
                }
            }

        # 4️⃣ Gemini fallback
        gemini_response = new_utils.structure_with_gemini(extracted_text, api_key)
        output = new_utils.format_response(gemini_response)

        return output or {"is_success": True, "raw_text": extracted_text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
