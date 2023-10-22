from fpdf import FPDF
from fastapi import FastAPI, APIRouter
import os
from typing import Optional
import datetime
from pydantic import BaseModel
from qrcode import QRCode
from uuid import uuid4
import boto3
import tempfile
from fastapi.responses import StreamingResponse
from io import BytesIO
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from ..utils import connect_to_db, get_plant_items

templates = Jinja2Templates(directory="qr_food_app/templates")
router = APIRouter()
app = FastAPI()

@router.get("/plants/", response_class=HTMLResponse)
async def read_items(request: Request, sort_by_expiration_date: bool = False, sort_order: Optional[str] = None):
    query_string = ""
    if sort_by_expiration_date:
        order = "ASC" if sort_order == "asc" else "DESC"
        query_string = f" ORDER BY fi.expiration_date {order}"
        query_string += ";"
    plant_items = await get_plant_items(query_string)
    return templates.TemplateResponse("plants_root.html", {"request": request, "food_items": plant_items})
