#!/usr/bin/env python3
# =============================================================================
# SCRIPT DE INICIALIZACIÓN DE BASE DE DATOS
# =============================================================================
# Este script inicializa y valida la base de datos Excel del sistema.
# Úsalo si tienes problemas al iniciar la aplicación.
# =============================================================================

import pandas as pd
from pathlib import Path
import sys
import traceback
from datetime import datetime

# Rutas de bases de datos
EXCEL_DB_PATH = Path(__file__).parent / "tickets_db.xlsx"
TECNICOS_DB_PATH = Path(__file__).parent / "tecnicos_db.xlsx"
EQUIPOS_DB_PATH = Path(__file__).parent / "equipos_db.xlsx"

# Columnas
COLUMNAS_DB = [
    "ID_TICKET", "TURNO", "FECHA_APERTURA", "USUARIO_AD", "HOSTNAME",
    "MAC_ADDRESS", "CATEGORIA", "PRIORIDAD", "DESCRIPCION", "ESTADO",
    "TECNICO_ASIGNADO", "NOTAS_RESOLUCION", "FECHA_CIERRE",
    "TIEMPO_ESTIMADO", "SATISFACCION"
]

COLUMNAS_TECNICOS = [
    "ID_TECNICO", "NOMBRE", "ESTADO", "ESPECIALIDAD",
    "TICKETS_ATENDIDOS", "TICKET_ACTUAL", "ULTIMA_ACTIVIDAD",
    "TELEFONO", "EMAIL"
]

COLUMNAS_EQUIPOS = [
    "MAC_ADDRESS", "NOMBRE_EQUIPO", "HOSTNAME", "USUARIO_ASIGNADO",
    "GRUPO", "UBICACION", "MARCA", "MODELO", "NUMERO_SERIE",
    "TIPO_EQUIPO", "SISTEMA_OPERATIVO", "PROCESADOR", "RAM_GB",
    "DISCO_GB", "FECHA_COMPRA", "GARANTIA_HASTA", "ESTADO_EQUIPO",
    "NOTAS", "FECHA_REGISTRO", "ULTIMA_CONEXION", "TOTAL_TICKETS"
]

def crear_db_tickets():
    """Crea la base de datos de tickets."""
    try:
        print(f"\n📋 Creando base de datos de tickets...")
        
        # Eliminar si existe
        if EXCEL_DB_PATH.exists():
            print(f"  ⚠️  Eliminando archivo existente: {EXCEL_DB_PATH.name}")
            EXCEL_DB_PATH.unlink()
        
        # Crear nueva
        df_vacio = pd.DataFrame(columns=COLUMNAS_DB)
        df_vacio.to_excel(EXCEL_DB_PATH, index=False, engine='openpyxl')
        print(f"  ✅ Base de datos de tickets creada: {EXCEL_DB_PATH}")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False

def crear_db_tecnicos():
    """Crea la base de datos de técnicos."""
    try:
        print(f"\n👥 Creando base de datos de técnicos...")
        
        # Eliminar si existe
        if TECNICOS_DB_PATH.exists():
            print(f"  ⚠️  Eliminando archivo existente: {TECNICOS_DB_PATH.name}")
            TECNICOS_DB_PATH.unlink()
        
        # Técnicos de ejemplo
        tecnicos_datos = [
            {
                "ID_TECNICO": "TEC001",
                "NOMBRE": "Carlos Mendoza",
                "ESTADO": "Disponible",
                "ESPECIALIDAD": "Soporte General",
                "TICKETS_ATENDIDOS": 0,
                "TICKET_ACTUAL": "",
                "ULTIMA_ACTIVIDAD": datetime.now(),
                "TELEFONO": "+34 600 123 456",
                "EMAIL": "carlos@empresa.com"
            },
            {
                "ID_TECNICO": "TEC002",
                "NOMBRE": "Patricia García",
                "ESTADO": "Disponible",
                "ESPECIALIDAD": "Redes",
                "TICKETS_ATENDIDOS": 0,
                "TICKET_ACTUAL": "",
                "ULTIMA_ACTIVIDAD": datetime.now(),
                "TELEFONO": "+34 600 234 567",
                "EMAIL": "patricia@empresa.com"
            },
            {
                "ID_TECNICO": "TEC003",
                "NOMBRE": "Juan López",
                "ESTADO": "Disponible",
                "ESPECIALIDAD": "Hardware",
                "TICKETS_ATENDIDOS": 0,
                "TICKET_ACTUAL": "",
                "ULTIMA_ACTIVIDAD": datetime.now(),
                "TELEFONO": "+34 600 345 678",
                "EMAIL": "juan@empresa.com"
            }
        ]
        
        df_tecnicos = pd.DataFrame(tecnicos_datos)
        df_tecnicos.to_excel(TECNICOS_DB_PATH, index=False, engine='openpyxl')
        print(f"  ✅ Base de datos de técnicos creada: {TECNICOS_DB_PATH}")
        print(f"     Con {len(tecnicos_datos)} técnicos de ejemplo")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False

def crear_db_equipos():
    """Crea la base de datos de equipos."""
    try:
        print(f"\n🖥️  Creando base de datos de equipos...")
        
        # Eliminar si existe
        if EQUIPOS_DB_PATH.exists():
            print(f"  ⚠️  Eliminando archivo existente: {EQUIPOS_DB_PATH.name}")
            EQUIPOS_DB_PATH.unlink()
        
        # Crear nueva vacía
        df_equipos = pd.DataFrame(columns=COLUMNAS_EQUIPOS)
        df_equipos.to_excel(EQUIPOS_DB_PATH, index=False, engine='openpyxl')
        print(f"  ✅ Base de datos de equipos creada: {EQUIPOS_DB_PATH}")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False

def validar_bases_datos():
    """Valida que todas las bases de datos sean accesibles."""
    print(f"\n✓ Validando bases de datos...")
    todos_ok = True
    
    for nombre, ruta, columnas in [
        ("Tickets", EXCEL_DB_PATH, COLUMNAS_DB),
        ("Técnicos", TECNICOS_DB_PATH, COLUMNAS_TECNICOS),
        ("Equipos", EQUIPOS_DB_PATH, COLUMNAS_EQUIPOS)
    ]:
        try:
            if not ruta.exists():
                print(f"  ❌ {nombre}: No existe")
                todos_ok = False
                continue
            
            df = pd.read_excel(ruta, engine='openpyxl', nrows=1)
            
            # Verificar columnas
            for col in columnas[:3]:
                if col not in df.columns:
                    print(f"  ⚠️  {nombre}: Falta columna '{col}'")
                    todos_ok = False
                    break
            else:
                print(f"  ✅ {nombre}: OK ({ruta.name})")
        except Exception as e:
            print(f"  ❌ {nombre}: Error - {e}")
            todos_ok = False
    
    return todos_ok

def main():
    """Función principal."""
    print("=" * 60)
    print("🔧 INICIALIZACIÓN DE BASE DE DATOS - Sistema de Tickets")
    print("=" * 60)
    print(f"\n📍 Ubicación: {Path(__file__).parent}")
    
    try:
        # Crear bases de datos
        ok1 = crear_db_tickets()
        ok2 = crear_db_tecnicos()
        ok3 = crear_db_equipos()
        
        if ok1 and ok2 and ok3:
            # Validar
            if validar_bases_datos():
                print("\n" + "=" * 60)
                print("✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
                print("=" * 60)
                print("\n✓ Ahora puedes ejecutar: python app_receptora.py")
                return 0
            else:
                print("\n⚠️  Bases de datos creadas pero con algunas advertencias")
                return 1
        else:
            print("\n❌ Error al crear las bases de datos")
            return 1
    
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
