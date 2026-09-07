from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password = Column(String(255), nullable=True)
    phone = Column(ARRAY(Integer), nullable=True)
    job_title = Column(String(255), nullable=True)
    line_manager_email = Column(String(255), nullable=True)
    entity = Column(String(255), nullable=True)
    role = Column(String(50), nullable=True)
    limit_lkr = Column(String(50), nullable=True)
    provinces = Column(ARRAY(String), nullable=True)
    reason = Column(String, nullable=True)
    request_ref = Column(String(50), nullable=True, unique=True, index=True)

    def __repr__(self):
        return f"<User(user_id={self.user_id}, email='{self.email}', first_name='{self.first_name}')>"
