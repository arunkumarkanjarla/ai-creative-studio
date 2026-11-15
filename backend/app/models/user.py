
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    String,
    text
)

from app.db.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    email = Column(String(255), unique=True, nullable=False, index=True)

    mobile = Column(String(20), nullable=True)

    password_hash = Column(String(255), nullable=False)

    role = Column(
        String(30),
        nullable=False,
        default="user"
    )

    can_access_image = Column(
        Boolean,
        nullable=False,
        default=False
    )

    can_access_audio = Column(
        Boolean,
        nullable=False,
        default=False
    )

    can_access_video = Column(
        Boolean,
        nullable=False,
        default=False
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
