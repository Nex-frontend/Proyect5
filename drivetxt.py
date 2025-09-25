import mysql.connector
from mysql.connector import Error


def conectar_bd():
    """Establece la conexión con la base de datos MySQL"""
    try:
        print("Intentando conectar a la base de datos...")
        print(f"Host: localhost, Puerto: 3306, Usuario: root, Base de datos: webquery_db")
       
        conexion = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='Host456my.sql',
            database='desc64',
            connection_timeout=5  # limitado en tiempo con timeout para no esperar demasiado
        )
        print("Conexión exitosa a la base de datos")
        return conexion
    except Error as e:
        import sys
        print("\n¡Error al conectar a la base de datos!")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje de error: {str(e)}")
        print("\nPor favor verifica lo siguiente:")
        print("1. Que el servidor MySQL esté en ejecución")
        print("2. Que el puerto 3306 sea el correcto (el puerto por defecto es 3306)")
        print("3. Que el usuario 'enrique' tenga los permisos necesarios")
        print("4. Que la base de datos 'webquery_db' exista")
        print("5. Que la contraseña sea correcta")
        return None


def insertar_registro(conexion, registro):
    """Inserta un registro en la tabla cto64"""
    cursor = None
    try:
        cursor = conexion.cursor()
       
        # Primero, obtener la estructura de la tabla
        cursor.execute("SHOW COLUMNS FROM cto64")
        columnas = [col[0] for col in cursor.fetchall()]
        print("\nColumnas en la tabla cto64:", ", ".join(columnas))
       
        # Construir dinámicamente la consulta SQL basada en las columnas existentes
        campos = []
        valores = []
       
        # Mapeo de campos del registro a las columnas de la tabla
        mapeo_campos = {
            'rfc': 'rfc',
            'nombre': 'nombre',
            'cadena1': 'cadena1',
            'tipo': 'tipo',
            'impor': 'impor',
            'cpto': 'cpto',
            'lote_actual': 'lote_actual',
            'qna': 'qna',
            'ptje': 'ptje',
            'observacio': 'observacio',
            'lote_anterior': 'lote_anterior',
            'qna_ini': 'qna_ini'
        }
       
        # Filtra solo las columnas que existen en la tabla
        campos_disponibles = []
        valores_a_insertar = []
       
        for campo_bd, campo_registro in mapeo_campos.items():
            if campo_bd in columnas:
                campos_disponibles.append(campo_bd)
                valor = registro.get(campo_registro, '')
                # Convertir a 0 los campos numéricos vacíos
                if campo_bd in ['impor', 'ptje'] and valor == '':
                    valor = '0'
                valores_a_insertar.append(valor)
       
        # Construir la consulta SQL dinámicamente
        placeholders = ', '.join(['%s'] * len(campos_disponibles))
        campos_sql = ', '.join([f'`{campo}`' for campo in campos_disponibles])
       
        sql = f"""
        INSERT INTO cto64 (
            {campos_sql}
        ) VALUES ({placeholders})
        """
       
        print("\nConsulta SQL:", sql)
        print("Valores:", valores_a_insertar)
       
        cursor.execute(sql, valores_a_insertar)
        conexion.commit()
        return cursor.rowcount
       
    except Error as e:
        print("\n¡Error al insertar registro!")
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Mensaje de error: {str(e)}")
        print(f"Consulta SQL: {sql if 'sql' in locals() else 'No disponible'}")
        print(f"Valores: {valores_a_insertar if 'valores_a_insertar' in locals() else 'No disponibles'}")
       
        if conexion:
            conexion.rollback()
        return 0
       
    finally:
        if cursor:
            cursor.close()


def validar_archivo(nombre_archivo):
    """
    Valida que el archivo exista y tenga el formato correcto.
   
    Returns:
        dict: {
            'valido': bool,
            'lineas': list o None,
            'mensaje': str
        }
    """
    try:
        with open(nombre_archivo, 'r', encoding='utf-8') as archivo:
            lineas = archivo.readlines()
           
            # Verificar cada línea
            for i, linea in enumerate(lineas, 1):
                # Eliminar el salto de línea al final
                linea = linea.rstrip('\n')
                # Validar longitud de la línea
                longitud_requerida = 100
                if len(linea) < longitud_requerida:
                    mensaje = f"Advertencia: La línea {i} no tiene la longitud mínima requerida (tiene {len(linea)} caracteres, se requieren {longitud_requerida})"
                    print(mensaje)
                if len(linea) != longitud_requerida:
                    return {
                        'valido': False,
                        'lineas': None,
                        'mensaje': f"Error en la línea {i}: longitud {len(linea)} caracteres (debe ser {longitud_requerida})"
                    }
           
            # Si llegamos aquí, todas las líneas son válidas
            return {
                'valido': True,
                'lineas': lineas,
                'mensaje': ""
            }
           
    except FileNotFoundError:
        return {
            'valido': False,
            'lineas': None,
            'mensaje': f"Error: El archivo {nombre_archivo} no fue encontrado."
        }
    except Exception as e:
        return {
            'valido': False,
            'lineas': None,
            'mensaje': f"Error al leer el archivo: {str(e)}"
        }


def definir_formato():
    """
    Define el formato del archivo de ancho fijo.
    Retorna una lista de tuplas con (nombre_campo, inicio, fin)
    """
    return [
        ("rfc", 0, 13),          # RFC (13 caracteres)
        ("nombre", 13, 43),      # Nombre (30 caracteres)
        ("cadena1", 43, 80),     # Cadena1 (37 caracteres)
        ("tipo", 80, 81),        # Tipo (1 carácter)
        ("impor", 81, 89),       # Importe (8 caracteres)
        ("cpto", 89, 91),        # Concepto (2 caracteres)
        ("lote_actual", 91, 92), # Lote actual (1 carácter)
        ("qna", 92, 98),         # QNA (6 caracteres)
        ("ptje", 98, 100),       # Puntaje (2 caracteres)
        ("observacio", 100, 147), # Observación (47 caracteres)
        ("lote_anterior", 147, 153), # Lote anterior (6 caracteres)
        ("qna_ini", 153, 159)    # QNA Inicial (6 caracteres)
    ]


def procesar_lineas(lineas, formato):
    """
    Procesa las líneas del archivo, convirtiendo cada una en un diccionario.
   
    Args:
        lineas (list): Lista de cadenas a procesar
        formato (list): Lista de tuplas con (nombre_campo, inicio, fin)
       
    Returns:
        list: Lista de diccionarios, donde cada uno representa un registro
    """
    registros = []
    for linea in lineas:
        # Crear un diccionario para el registro actual
        registro = {}
        for campo, inicio, fin in formato:
            # Eliminar espacios en blanco al inicio y final de cada campo
            registro[campo] = linea[inicio:fin].strip()
        registros.append(registro)
    return registros


def main():
    # Nombre del archivo a leer
    nombre_archivo = "ejemplo.txt"
   
    # 1. Primero validar el archivo
    print(f"Validando archivo '{nombre_archivo}'...")
    resultado_validacion = validar_archivo(nombre_archivo)
   
    if not resultado_validacion['valido']:
        print(f"Error: {resultado_validacion['mensaje']}")
        return
   
    # 2. Si el archivo es válido, procesar las líneas
    print("\n¡Archivo validado correctamente!\n")
   
    # 3. Definir el formato del archivo
    formato = definir_formato()
   
    # 4. Procesar las líneas válidas
    registros = procesar_lineas(resultado_validacion['lineas'], formato)
   
    # 5. Mostrar el contenido procesado
    print(f"Contenido del archivo '{nombre_archivo}':\n")
   
    for i, registro in enumerate(registros, 1):
        print(f"\n=== Registro {i} ===")
        for campo, valor in registro.items():
            print(f"{campo:15}: {valor}")
   
    # 6. Insertar registros en la base de datos
    print("\nConectando a la base de datos...")
    conexion = conectar_bd()
   
    if conexion:
        try:
            registros_insertados = 0
            for registro in registros:
                registros_insertados += insertar_registro(conexion, registro)
           
            print(f"\nResumen de la carga a la base de datos:")
            print(f"- Total de registros procesados: {len(registros)}")
            print(f"- Registros insertados correctamente: {registros_insertados}")
           
        except Exception as e:
            print(f"Error durante la inserción de registros: {e}")
        finally:
            if conexion.is_connected():
                conexion.close()
                print("\nConexión a la base de datos cerrada")
    else:
        print("\nNo se pudo establecer conexión con la base de datos")
   
    # 7. Mostrar resumen final
    print(f"\n{'='*50}")
    print("RESUMEN FINAL:")
    print(f"- Total de registros procesados: {len(registros)}")
    print("\nEstructura de los campos:")
    for campo, inicio, fin in formato:
        print(f"- {campo:15}: posiciones {inicio:3} a {fin-1:3} (longitud: {fin-inicio})")
    print(f"\nLongitud total del registro: {sum(fin-inicio for _, inicio, fin in formato)} caracteres")


if __name__ == "__main__":
    main()
