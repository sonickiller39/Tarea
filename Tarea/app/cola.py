class ColaMisiones:
    def __init__(self):
        self.elementos = []
    
    def encolar(self, mision):
        """Añade una misión al final de la cola"""
        self.elementos.append(mision)
        return mision
    
    def desencolar(self):
        """Elimina y retorna la primera misión de la cola"""
        if self.esta_vacia():
            return None
        return self.elementos.pop(0)
    
    def primero(self):
        """Retorna la primera misión sin eliminarla"""
        if self.esta_vacia():
            return None
        return self.elementos[0]
    
    def esta_vacia(self):
        """Verifica si la cola está vacía"""
        return len(self.elementos) == 0
    
    def tamaño(self):
        """Retorna la cantidad de misiones en la cola"""
        return len(self.elementos)