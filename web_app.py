from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db, User, Purchase
import qrcode
from datetime import datetime
import os
from bot import generate_qr_code
from pydantic import BaseModel

app = FastAPI()

# Create directories for static files
os.makedirs("static", exist_ok=True)
os.makedirs("static/qr", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class QRVerification(BaseModel):
    qr_code: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse(url="/admin")

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "users": users}
    )

@app.get("/guest/{telegram_id}", response_class=HTMLResponse)
async def guest_panel(request: Request, telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Get latest unverified purchase (active QR code)
    active_purchase = db.query(Purchase).filter(
        Purchase.user_id == user.id,
        Purchase.verified == False
    ).order_by(desc(Purchase.purchase_date)).first()
    
    # Get last 10 purchases
    purchases = db.query(Purchase).filter(
        Purchase.user_id == user.id
    ).order_by(desc(Purchase.purchase_date)).limit(10).all()
    
    return templates.TemplateResponse(
        "guest.html",
        {
            "request": request,
            "user": user,
            "purchases": purchases,
            "active_purchase": active_purchase
        }
    )

@app.post("/generate_qr/{user_id}")
async def generate_purchase_qr(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Check if user has unverified QR codes
    active_qr = db.query(Purchase).filter(
        Purchase.user_id == user.id,
        Purchase.verified == False
    ).first()
    
    if active_qr:
        return {
            "qr_code": active_qr.qr_code,
            "is_free": active_qr.is_free,
            "message": "У пользователя уже есть активный QR-код"
        }
    
    # Generate QR code
    qr_code_data = generate_qr_code()
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_code_data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code image
    qr_image_path = f"static/qr/{qr_code_data}.png"
    qr_image.save(qr_image_path)
    
    # Create purchase record
    purchase = Purchase(
        user_id=user.id,
        qr_code=qr_code_data,
        is_free=(user.purchases_count + 1) % 6 == 0
    )
    db.add(purchase)
    
    # Update user's purchase count
    user.purchases_count += 1
    if purchase.is_free:
        user.total_free_hookahs += 1
    
    db.commit()
    
    return {
        "qr_code": qr_code_data,
        "is_free": purchase.is_free,
        "message": "QR-код успешно создан"
    }

@app.post("/verify_qr")
async def verify_qr(qr_data: QRVerification, db: Session = Depends(get_db)):
    purchase = db.query(Purchase).filter(Purchase.qr_code == qr_data.qr_code).first()
    
    if not purchase:
        return {
            "success": False,
            "message": "QR код не найден"
        }
    
    if purchase.verified:
        return {
            "success": False,
            "message": "QR код уже был использован"
        }
    
    user = db.query(User).filter(User.id == purchase.user_id).first()
    
    # Mark purchase as verified
    purchase.verified = True
    db.commit()
    
    return {
        "success": True,
        "message": f"QR код подтвержден! {'Бесплатный' if purchase.is_free else 'Обычный'} кальян для пользователя {user.username or 'Без имени'}"
    } 