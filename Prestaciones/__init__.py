"""Inicialización del proyecto Prestaciones.

Intenta usar mysqlclient; si no está disponible, instala PyMySQL como MySQLdb.
"""

try:
    import MySQLdb  # noqa: F401
except Exception:
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except Exception:
        # Si no hay PyMySQL, Django fallará al intentar conectar; se resolverá tras instalar dependencias.
        pass
