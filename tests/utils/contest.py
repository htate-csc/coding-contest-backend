from sqlmodel import Session

from app import crud
from app.models import Contest, ContestCreate
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def create_random_Contest(db: Session) -> Contest:
    user = create_random_user(db)
    owner_id = user.id
    assert owner_id is not None
    title = random_lower_string()
    description = random_lower_string()
    Contest_in = ContestCreate(title=title, description=description)
    return crud.create_Contest(session=db, Contest_in=Contest_in, owner_id=owner_id)
