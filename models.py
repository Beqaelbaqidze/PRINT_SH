from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base

company_surveyor = Table(
    'company_surveyor', Base.metadata,
    Column('company_id', Integer, ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True),
    Column('surveyor_id', Integer, ForeignKey('surveyors.id', ondelete='CASCADE'), primary_key=True)
)

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String)
    company_id = Column(String, unique=True)
    email = Column(String)
    mobile_number = Column(String)
    director = Column(String)
    surveyors = relationship("Surveyor", secondary=company_surveyor, back_populates="companies")

class Surveyor(Base):
    __tablename__ = "surveyors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    companies = relationship("Company", secondary=company_surveyor, back_populates="surveyors")
    computers = relationship("Computer", back_populates="surveyor")

class Computer(Base):
    __tablename__ = "computers"
    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String, unique=True)
    surveyor_id = Column(Integer, ForeignKey("surveyors.id", ondelete='CASCADE'))
    surveyor = relationship("Surveyor", back_populates="computers")
    licenses = relationship("License", back_populates="computer")

class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id", ondelete='CASCADE'))
    paid = Column(Boolean, default=False)
    expire_date = Column(Date)
    computer = relationship("Computer", back_populates="licenses")
