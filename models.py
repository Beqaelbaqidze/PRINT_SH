from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

company_surveyor = Table(
    'company_surveyor',
    Base.metadata,
    Column('company_id', Integer, ForeignKey('companies.id')),
    Column('surveyor_id', Integer, ForeignKey('surveyors.id'))
)

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True)
    company_name = Column(String, nullable=False)
    company_id = Column(String, unique=True, nullable=False)
    email = Column(String)
    mobile_number = Column(String)
    director = Column(String)
    temporary = Column(Boolean, default=True)

    surveyors = relationship("Surveyor", secondary=company_surveyor, back_populates="companies")


class Surveyor(Base):
    __tablename__ = 'surveyors'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    temporary = Column(Boolean, default=True)

    companies = relationship("Company", secondary=company_surveyor, back_populates="surveyors")
    computers = relationship("Computer", back_populates="surveyor")


class Computer(Base):
    __tablename__ = 'computers'

    id = Column(Integer, primary_key=True)
    serial_number = Column(String, unique=True, nullable=False)
    surveyor_id = Column(Integer, ForeignKey('surveyors.id'))
    temporary = Column(Boolean, default=True)

    surveyor = relationship("Surveyor", back_populates="computers")
    licenses = relationship("License", back_populates="computer")


class License(Base):
    __tablename__ = 'licenses'

    id = Column(Integer, primary_key=True)
    computer_id = Column(Integer, ForeignKey('computers.id'))
    paid = Column(Boolean, default=False)
    expire_date = Column(Date, nullable=False)
    temporary = Column(Boolean, default=True)

    computer = relationship("Computer", back_populates="licenses")
