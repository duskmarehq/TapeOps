import enum


class RolUsuario(str, enum.Enum):
    admin = "admin"
    operario = "operario"


class EstadoPedido(str, enum.Enum):
    pendiente = "pendiente"
    asignado = "asignado"
    en_ruta = "en_ruta"
    entregado = "entregado"
    fallido = "fallido"


class EstadoRuta(str, enum.Enum):
    planificada = "planificada"
    en_curso = "en_curso"
    finalizada = "finalizada"


class EstadoStop(str, enum.Enum):
    pendiente = "pendiente"
    completado = "completado"
    fallido = "fallido"


class TipoIncidencia(str, enum.Enum):
    retraso = "retraso"
    ruta_bloqueada = "ruta_bloqueada"
    entrega_fallida = "entrega_fallida"
