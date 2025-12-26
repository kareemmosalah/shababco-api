"""
Attendee authentication and order management routes.
Handles signup, signin, and order/ticket retrieval for customers.
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import CurrentAttendee, SessionDep
from app.core import security
from app.core.config import settings
from app.models import (
    Attendee,
    AttendeePublic,
    AttendeeSignin,
    AttendeeSignup,
    Message,
    Token,
)

router = APIRouter(prefix="/attendees", tags=["attendees"])



@router.post("/signup", response_model=AttendeePublic, status_code=status.HTTP_201_CREATED)
def signup(*, session: SessionDep, attendee_in: AttendeeSignup) -> Attendee:
    """
    Create new attendee account.
    
    Matches Figma signup form with fields:
    - email (required)
    - password (required)
    - first_name (required)
    - last_name (required)
    - phone (optional)
    - birthdate (optional)
    - country (optional)
    - city (optional)
    """
    # Check if attendee already exists
    attendee = crud.get_attendee_by_email(session=session, email=attendee_in.email)
    if attendee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )
    
    # Create new attendee
    attendee = crud.create_attendee(session=session, attendee_create=attendee_in)
    return attendee


@router.post("/signin", response_model=Token)
def signin(*, session: SessionDep, attendee_in: AttendeeSignin) -> Token:
    """
    Attendee signin with email and password.
    
    Returns JWT access token for authenticated requests.
    """
    # Authenticate attendee
    attendee = crud.authenticate_attendee(
        session=session, 
        email=attendee_in.email, 
        password=attendee_in.password
    )
    
    if not attendee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        attendee.id, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token)


@router.post("/signin/oauth", response_model=Token)
def signin_oauth(
    session: SessionDep, 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible signin endpoint.
    
    Allows using OAuth2 password flow for attendee authentication.
    Username field should contain email.
    """
    attendee = crud.authenticate_attendee(
        session=session,
        email=form_data.username,  # OAuth2 uses 'username' field
        password=form_data.password
    )
    
    if not attendee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        attendee.id, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token)


@router.get("/me", response_model=AttendeePublic)
def get_current_attendee_info(current_attendee: CurrentAttendee) -> Attendee:
    """
    Get current attendee information.
    
    Requires authentication via JWT token.
    """
    return current_attendee



@router.get("/me/orders")
def get_my_orders(
    session: SessionDep,
    # TODO: Add CurrentAttendee dependency
):
    """
    Get all orders for authenticated attendee.
    
    Returns orders with ticket details from PostgreSQL (fast lookup).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented - requires order sync via webhooks"
    )


@router.get("/me/tickets")
def get_my_tickets(
    session: SessionDep,
    # TODO: Add CurrentAttendee dependency
):
    """
    Get all tickets for authenticated attendee.
    
    Includes QR codes for event check-in.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented - requires order sync via webhooks"
    )
