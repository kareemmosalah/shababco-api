"""
Google OAuth authentication routes for attendees.
Handles "Log in with Google" and "Sign up with Google" flows.

Currently returns 'not available yet' until Google OAuth credentials are configured.
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/attendees/auth/google", tags=["attendees", "oauth"])


@router.get("/login")
async def google_login():
    """
    Initiate Google OAuth flow.
    
    Returns authorization URL for frontend to redirect user to Google.
    
    Currently not available - returns 501.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OAuth is not available yet. Please use email/password signup for now."
    )


@router.get("/callback")
async def google_callback(code: str, state: str | None = None):
    """
    Handle OAuth callback from Google.
    
    Exchanges authorization code for access token,
    gets user info, creates/finds attendee, and returns JWT.
    
    Currently not available - returns 501.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OAuth is not available yet. Please use email/password signin for now."
    )


@router.post("/link")
async def link_google_account(code: str):
    """
    Link Google account to existing attendee.
    
    For users who signed up with email/password and want to add Google login.
    Requires authentication.
    
    Currently not available - returns 501.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google account linking is not available yet."
    )
