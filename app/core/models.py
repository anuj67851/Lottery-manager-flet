from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    role: Mapped[bool] = mapped_column(Boolean)
    username: Mapped[int] = mapped_column(Integer)
    password: Mapped[str] = mapped_column(String(30))
