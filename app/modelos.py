from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()
personaje_mision = Table(
    'personaje_mision',
    Base.metadata,
    Column('personaje_id', Integer, ForeignKey('personajes.id'), primary_key=True),
    Column('mision_id', Integer, ForeignKey('misiones.id'), primary_key=True),
    Column('posicion_cola', Integer, nullable=False),
    Column('asignada_en', DateTime, default=datetime.datetime.utcnow)
)

class Personaje(Base):
    __tablename__ = 'personajes'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    nivel = Column(Integer, default=1)
    experiencia = Column(Integer, default=0)
    misiones = relationship("Mision", secondary=personaje_mision, back_populates="personajes")

class Mision(Base):
    __tablename__ = 'misiones'
    
    id = Column(Integer, primary_key=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(String)
    recompensa_xp = Column(Integer, default=10)
    personajes = relationship("Personaje", secondary=personaje_mision, back_populates="misiones")