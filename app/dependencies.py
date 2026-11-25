from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import Depends
from app.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]
