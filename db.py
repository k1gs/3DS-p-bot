from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Topic(Base):
    __tablename__ = 'topics'
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, unique=True, nullable=False)
    title = Column(String)
    size = Column(String)
    seeds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine('sqlite:///bot_db.sqlite')
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def add_user(telegram_id: int):
    with Session() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            session.add(User(telegram_id=telegram_id))
            session.commit()

def is_topic_new(topic_id: int) -> bool:
    with Session() as session:
        return session.query(Topic).filter_by(topic_id=topic_id).first() is None

def add_topic(topic_id: int, title: str, size: str, seeds: int):
    with Session() as session:
        if is_topic_new(topic_id):
            session.add(Topic(topic_id=topic_id, title=title, size=size, seeds=seeds))
            session.commit()

def get_all_users():
    with Session() as session:
        return [user.telegram_id for user in session.query(User).all()]
