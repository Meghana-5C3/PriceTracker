import hashlib
import uuid
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from data.core.database import get_session, User, RewardTransaction

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")

def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Email already registered"
        })
    
    # Create user
    new_user = User(
        email=email,
        hashed_password=hash_password(password),
        referral_code=str(uuid.uuid4())[:8],
        redeemable_points=100, # Welcome bonus
        lifetime_earned_points=100
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Add welcome transaction
    welcome_tx = RewardTransaction(
        user_id=new_user.id,
        amount=100,
        type="welcome_bonus",
        status="confirmed"
    )
    db.add(welcome_tx)
    db.commit()
    
    return RedirectResponse(url="/auth/login?msg=Registered successfully", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, msg: str = None):
    return templates.TemplateResponse("auth/login.html", {"request": request, "msg": msg})

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.hashed_password != hash_password(password):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid email or password"
        })
    
    # Set session
    request.session["user_id"] = user.id
    request.session["user_email"] = user.email
    
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("auth/forgot-password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form(...)):
    # Mock email sending
    return templates.TemplateResponse("auth/forgot-password.html", {
        "request": request,
        "msg": f"An email has been sent to {email} with instructions to reset your password."
    })
