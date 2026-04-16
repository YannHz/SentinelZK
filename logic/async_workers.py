"""
logic/async_workers.py
Gestor de hilos secundarios para delegar operaciones pesadas
y mantener la UI de customtkinter sin congelamientos.
"""
import threading
import queue
from typing import Callable, Any


class WorkerThread(threading.Thread):
    """
    Hilo reutilizable que ejecuta una tarea y notifica el resultado
    mediante un callback en el hilo principal.
    
    Uso:
        worker = WorkerThread(tarea=mi_funcion, args=(arg1,), callback=mi_callback)
        worker.start()
    """

    def __init__(self, tarea: Callable, args: tuple = (), callback: Callable = None):
        super().__init__(daemon=True)  # Se cierra con la ventana principal
        self._tarea    = tarea
        self._args     = args
        self._callback = callback

    def run(self):
        try:
            resultado = self._tarea(*self._args)
            if self._callback:
                self._callback(resultado, error=None)
        except Exception as exc:
            if self._callback:
                self._callback(None, error=str(exc))


class TaskQueue:
    """
    Cola de tareas para serializar operaciones de base de datos
    y evitar conflictos de escritura concurrente en SQLite.
    """

    def __init__(self):
        self._queue  = queue.Queue()
        self._worker = threading.Thread(target=self._procesar, daemon=True)
        self._worker.start()

    def encolar(self, tarea: Callable, args: tuple = (), callback: Callable = None):
        self._queue.put((tarea, args, callback))

    def _procesar(self):
        while True:
            tarea, args, callback = self._queue.get()
            try:
                resultado = tarea(*args)
                if callback:
                    callback(resultado, error=None)
            except Exception as exc:
                if callback:
                    callback(None, error=str(exc))
            finally:
                self._queue.task_done()


# Instancia global de la cola de tareas (importar desde otros módulos)
task_queue = TaskQueue()
