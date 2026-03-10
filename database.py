from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

db_engine = create_engine("sqlite:///placement.db", echo=False)

db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
)

Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    import models
    Base.metadata.create_all(bind=db_engine)

    from models import User
    from werkzeug.security import generate_password_hash

    admin_user = db_session.query(User).filter_by(email="placement_admin@college.edu").first()
    if admin_user is None:
        admin_user = User(
            name="Placement Admin",
            email="placement_admin@college.edu",
            password=generate_password_hash("admin123"),
            role="admin",
            status="active",
        )
        db_session.add(admin_user)
        db_session.commit()
        print("Default admin created -> placement_admin@college.edu / admin123")
    else:
        print("Admin already exists, skipping seed.")
