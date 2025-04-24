from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.query_bus import query_bus
from app.application.queries import GetUserByEmailQuery, GetUserByIdQuery, GetUserProfileQuery, ListAdminsQuery, ListUsersQuery
from app.infrastructure.database import get_db
from app.application.handlers import AuthCommandHandler, EditUserHandler, GetUserByIdHandler, GetUserProfileHandler, ListUsersHandler, RegisterUserHandler, UpdateUserRoleHandler, UserQueryHandler
from app.application.commands import EditUserCommand, LoginUserCommand, UpdateUserRoleCommand
from app.infrastructure.models import User
from app.security import get_current_complete_user, get_current_user
from fastapi import Form
from app.application.handlers import command_bus

router = APIRouter(prefix="/users", tags=["Users"])
templates = Jinja2Templates(directory="app/templates")  # Path to your templates folder

@router.get("/sign-up", response_class=HTMLResponse)
async def render_sign_up_form(request: Request):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse("sign_up.html", {"request": request, "is_logged_in": is_logged_in})

@router.get("/login", response_class=HTMLResponse)
async def render_login_form(request: Request):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse("login.html", {"request": request, "is_logged_in": is_logged_in})

@router.get("/users", response_class=HTMLResponse)
def render_list_users(
    request: Request,
    page: int = Query(1, ge=1),  # Default to page 1
    page_size: int = Query(10, ge=1, le=100),  # Default page size 10 
    current_user: User = Depends(get_current_user)
):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    # Create the query instance
    query = ListUsersQuery(page=page, page_size=page_size)
    # Pass the query to the handler
    users = query_bus.handle(query)
    
    return templates.TemplateResponse("list_users.html", {
        "request": request, 
        "is_logged_in": is_logged_in, 
        "users": users,
        "page": page,
        "page_size": page_size
    }) 

@router.get("/profile", response_class=HTMLResponse)
async def render_login_form(request: Request, current_user: User = Depends(get_current_user)):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    print(f"Current user: {current_user}")
    # Create query command instance
    query = GetUserByEmailQuery(email=current_user)
    try:
        user_profile = query_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "is_logged_in": is_logged_in, 
        "user": user_profile
    })

@router.get("/edit", response_class=HTMLResponse)
async def render_edit_form(request: Request, current_user: User = Depends(get_current_user)):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    print(f"Current user: {current_user}")
    # Create query command instance
    query = GetUserByEmailQuery(email=current_user)
    try:
        user_edit = query_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return templates.TemplateResponse("edit_user.html", {
        "request": request, 
        "is_logged_in": is_logged_in, 
        "user": user_edit
    })

@router.post("/sign-up", status_code=201)
async def sign_up(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    handler = RegisterUserHandler()
    try:
        # Create a dictionary to simulate the original UserSignUp object
        user_data = {"name": name, "email": email, "password": password}
        result = handler.handle(user_data)
        return RedirectResponse(url="/users/login", status_code=302)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    print(f"Logging in user with email: {email}")

    # Dispatch the command via the handler
    try:
        command = LoginUserCommand(email=email, password=password)  # Create the command correctly
        access_token = command_bus.handle(command)
        print("Token created")
    except ValueError as e:
        raise HTTPException(status_code=401, detail='Invalid email or password')

    # Set cookie and redirect
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=1800
    )
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/users/login", status_code=302)
    response.delete_cookie(key="access_token")  # Remove the token
    return response

@router.put("/{user_id}")
async def edit_user(
    user_id: int,
    update_data: EditUserCommand
):
    # Pass the request to the handler
    handler = EditUserHandler()
    updated_user = handler.handle(user_id, update_data)
    return {"message": "User updated successfully!", "user": updated_user}

@router.post("update/{user_id}")
async def edit_user(
    user_id: int,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    update_data = EditUserCommand(name=name, email=email, password=password)
    # Pass the request to the handler
    handler = EditUserHandler()
    updated_user = handler.handle(user_id, update_data)
    return {"message": "User updated successfully!", "user": updated_user}

@router.get("/users/profile")
async def get_user_profile(current_user: User = Depends(get_current_complete_user)):
    print(f"Getting user profile for user: {current_user.id}")
    # Create query command instance
    query = GetUserProfileQuery(user_id=current_user.id)
    try:
        user_profile = query_bus.handle(query)
        return {"user": user_profile}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.put("/{user_id}/role")
def update_user_role(
    user_id: int,
    command: UpdateUserRoleCommand
):    
    try:
        result = command_bus.handle(command)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}")
def get_user_by_id(user_id: int):
    # Create and process the query
    query = GetUserByIdQuery(user_id=user_id)
    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/admins/")
def list_admins(
      # Default page size is 10
    page: int = Query(1, ge=1),  # Default page number is 1
    page_size: int = Query(10, ge=1, le=100)
):
    try:
        
        print(f"Listing admins, page: {page}, page_size: {page_size}")
        query = ListAdminsQuery(page=page, page_size=page_size)
        result = query_bus.handle(query)
        return {"admins": result}
    except ValueError as e:
        print(f"Error listing admins: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))