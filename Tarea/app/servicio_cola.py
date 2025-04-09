from fastapi import HTTPException
from sqlalchemy.orm import Session
from .modelos import Mision, personaje_mision
from .cola import ColaMisiones

class ServicioColaMisiones:
    def __init__(self, db: Session):
        self.db = db
        self.cache_colas = {}  
    
    def obtener_cola_personaje(self, personaje_id: int) -> ColaMisiones:
        """Obtiene la cola de misiones para un personaje. Si no existe, la crea."""
        if personaje_id not in self.cache_colas:
            self.cache_colas[personaje_id] = ColaMisiones()
            
            # Cargar misiones de la bd
            misiones = self.db.query(Mision, personaje_mision.c.posicion_cola).join(
                personaje_mision, Mision.id == personaje_mision.c.mision_id
            ).filter(
                personaje_mision.c.personaje_id == personaje_id
            ).order_by(personaje_mision.c.posicion_cola).all()
            
            for mision, _ in misiones:
                self.cache_colas[personaje_id].encolar(mision)
                
        return self.cache_colas[personaje_id]
    
    def encolar_mision(self, personaje_id: int, mision_id: int):
        """Añade una misión a la cola de un personaje."""
        mision = self.db.query(Mision).filter(Mision.id == mision_id).first()
        if not mision:
            raise HTTPException(status_code=404, detail="Misión no encontrada")
        cola = self.obtener_cola_personaje(personaje_id)
        cola.encolar(mision)
        return mision
    
    def desencolar_mision(self, personaje_id: int):
        """Elimina y retorna la primera misión de la cola de un personaje."""
        cola = self.obtener_cola_personaje(personaje_id)
        if cola.esta_vacia():
            return None
        # Obtiene la primera misión
        mision = cola.desencolar()
        return mision
    
    def obtener_tamaño_cola(self, personaje_id: int) -> int:
        """Retorna la cantidad de misiones en la cola de un personaje."""
        cola = self.obtener_cola_personaje(personaje_id)
        return cola.tamaño()
    
    def obtener_primera_mision(self, personaje_id: int):
        """Retorna la primera misión en la cola sin eliminarla."""
        cola = self.obtener_cola_personaje(personaje_id)
        return cola.primero()