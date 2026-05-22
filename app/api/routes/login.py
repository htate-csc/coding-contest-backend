from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.models import Message, NewPassword, Token, UserPublic, UserUpdate
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.authenticate(
        session=session, login_id=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect login ID or password")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{login_id}")
def recover_password(login_id: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_login_id(session=session, login_id=login_id)

    # Always return the same response to prevent enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = generate_password_reset_token(login_id=login_id)
        email_data = generate_reset_password_email(
            login_id=login_id, token=password_reset_token
        )
        send_email(
            email_to=login_id,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that login ID is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    login_id = verify_password_reset_token(token=body.token)
    if not login_id:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_login_id(session=session, login_id=login_id)
    if not user:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise HTTPException(status_code=400, detail="Invalid token")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{login_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(login_id: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_login_id(session=session, login_id=login_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this login ID does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(login_id=login_id)
    email_data = generate_reset_password_email(
        login_id=login_id, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )
