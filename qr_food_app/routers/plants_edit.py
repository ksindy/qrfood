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

router = APIRouter()
app = FastAPI()
