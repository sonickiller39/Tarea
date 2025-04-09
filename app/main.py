from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import List, Optional

from .modelos import Base, Personaje, Mision, personaje_mision
from .servicio_cola import ServicioColaMisiones

URL_BASE_DATOS = "sqlite:///./rpg_misiones.db"
motor = create_engine(URL_BASE_DATOS)
SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)
Base.metadata.create_all(bind=motor)

app = FastAPI(title="Sistema de Misiones RPG")

class CreacionPersonaje(BaseModel):
    nombre: str
    nivel: int = 1
    experiencia: int = 0

class RespuestaPersonaje(CreacionPersonaje):
    id: int
    
    class Config:
        from_attributes = True  

class CreacionMision(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    recompensa_xp: int = 10

class RespuestaMision(CreacionMision):
    id: int
    
    class Config:
        from_attributes = True

class RespuestaPersonajeMision(BaseModel):
    mision: RespuestaMision
    posicion_cola: int
    
    class Config:
        from_attributes = True


def obtener_db():
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint: Crear nuevo personaje
@app.post("/personajes", response_model=RespuestaPersonaje)
def crear_personaje(personaje: CreacionPersonaje, db: Session = Depends(obtener_db)):
    db_personaje = Personaje(nombre=personaje.nombre, nivel=personaje.nivel, experiencia=personaje.experiencia)
    db.add(db_personaje)
    db.commit()
    db.refresh(db_personaje)
    return db_personaje

# Endpoint: Crear nueva misión
@app.post("/misiones", response_model=RespuestaMision)
def crear_mision(mision: CreacionMision, db: Session = Depends(obtener_db)):
    db_mision = Mision(titulo=mision.titulo, descripcion=mision.descripcion, recompensa_xp=mision.recompensa_xp)
    db.add(db_mision)
    db.commit()
    db.refresh(db_mision)
    return db_mision

# Endpoint: Aceptar misión (encolar)
@app.post("/personajes/{personaje_id}/misiones/{mision_id}", response_model=RespuestaPersonajeMision)
def aceptar_mision(personaje_id: int, mision_id: int, db: Session = Depends(obtener_db)):
    personaje = db.query(Personaje).filter(Personaje.id == personaje_id).first()
    mision = db.query(Mision).filter(Mision.id == mision_id).first()
    
    if not personaje or not mision:
        raise HTTPException(status_code=404, detail="Personaje o misión no encontrada")
    
    existente = db.query(personaje_mision).filter_by(
        personaje_id=personaje_id, 
        mision_id=mision_id
    ).first()
    
    if existente:
        raise HTTPException(status_code=400, detail="Esta misión ya está asignada al personaje")
    
    posicion_maxima = db.query(personaje_mision.c.posicion_cola).filter_by(
        personaje_id=personaje_id
    ).order_by(desc(personaje_mision.c.posicion_cola)).first()
    
    siguiente_posicion = 1 if not posicion_maxima else posicion_maxima[0] + 1
    
    stmt = personaje_mision.insert().values(
        personaje_id=personaje_id,
        mision_id=mision_id,
        posicion_cola=siguiente_posicion
    )
    db.execute(stmt)
    db.commit()
    
    servicio_cola = ServicioColaMisiones(db)
    servicio_cola.encolar_mision(personaje_id, mision_id)
    
    return {"mision": mision, "posicion_cola": siguiente_posicion}

# Endpoint: Completar misión (desencolar + sumar XP)
@app.post("/personajes/{personaje_id}/completar", response_model=RespuestaPersonaje)
def completar_mision(personaje_id: int, db: Session = Depends(obtener_db)):
    personaje = db.query(Personaje).filter(Personaje.id == personaje_id).first()
    if not personaje:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    
    # Buscar la primera misión en la cola
    relacion_mision = db.query(personaje_mision).filter_by(
        personaje_id=personaje_id
    ).order_by(personaje_mision.c.posicion_cola).first()
    
    if not relacion_mision:
        raise HTTPException(status_code=404, detail="El personaje no tiene misiones pendientes")
    
    mision = db.query(Mision).filter(Mision.id == relacion_mision.mision_id).first()
    
    personaje.experiencia += mision.recompensa_xp
    
    personaje.nivel = (personaje.experiencia // 100) + 1
    
    db.query(personaje_mision).filter_by(
        personaje_id=personaje_id,
        mision_id=relacion_mision.mision_id
    ).delete()
    
    servicio_cola = ServicioColaMisiones(db)
    servicio_cola.desencolar_mision(personaje_id)
    
    misiones_restantes = db.query(personaje_mision).filter_by(
        personaje_id=personaje_id
    ).order_by(personaje_mision.c.posicion_cola).all()
    
    for i, rel_mision in enumerate(misiones_restantes, 1):
        db.execute(
            personaje_mision.update().where(
                (personaje_mision.c.personaje_id == personaje_id) &
                (personaje_mision.c.mision_id == rel_mision.mision_id)
            ).values(posicion_cola=i)
        )
    
    db.commit()
    db.refresh(personaje)
    return personaje

# Endpoint: Listar misiones en orden FIFO
@app.get("/personajes/{personaje_id}/misiones", response_model=List[RespuestaPersonajeMision])
def listar_misiones_personaje(personaje_id: int, db: Session = Depends(obtener_db)):
    personaje = db.query(Personaje).filter(Personaje.id == personaje_id).first()
    if not personaje:
        raise HTTPException(status_code=404, detail="Personaje no encontrado")
    
    resultado = []
    misiones = db.query(Mision, personaje_mision.c.posicion_cola).join(
        personaje_mision, Mision.id == personaje_mision.c.mision_id
    ).filter(
        personaje_mision.c.personaje_id == personaje_id
    ).order_by(personaje_mision.c.posicion_cola).all()
    
    for mision, posicion_cola in misiones:
        resultado.append({"mision": mision, "posicion_cola": posicion_cola})
    
    return resultado