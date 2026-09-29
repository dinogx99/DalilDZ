import os
from sqlalchemy import create_engine,String,Text,DateTime,ForeignKey,JSON
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker
from datetime import datetime,timezone
DB=os.getenv('DATABASE_URL','sqlite:///./dalildz.db');engine=create_engine(DB,connect_args={'check_same_thread':False} if DB.startswith('sqlite') else {});Session=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase):pass
class Case(Base):
 __tablename__='cases';id:Mapped[str]=mapped_column(String,primary_key=True);name:Mapped[str]=mapped_column(String);claims:Mapped[dict]=mapped_column(JSON,default=dict);created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Document(Base):
 __tablename__='documents';id:Mapped[str]=mapped_column(String,primary_key=True);case_id:Mapped[str]=mapped_column(ForeignKey('cases.id',ondelete='CASCADE'));filename:Mapped[str]=mapped_column(String);mime:Mapped[str]=mapped_column(String);sha256:Mapped[str]=mapped_column(String);text:Mapped[str]=mapped_column(Text,default='');extracted:Mapped[dict]=mapped_column(JSON,default=dict)
class Evidence(Base):
 __tablename__='evidence';id:Mapped[str]=mapped_column(String,primary_key=True);case_id:Mapped[str]=mapped_column(String,index=True);field:Mapped[str]=mapped_column(String,index=True);submitted:Mapped[str|None]=mapped_column(Text,nullable=True);observed:Mapped[str|None]=mapped_column(Text,nullable=True);status:Mapped[str]=mapped_column(String,index=True);source:Mapped[str]=mapped_column(String);metadata_json:Mapped[dict]=mapped_column(JSON,default=dict);checked_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
def init_db():Base.metadata.create_all(engine)
