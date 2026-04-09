"""Tests enterprise para auditoria de ticket_log.

Cobertura principal:
- Inmutabilidad del log (bloqueo UPDATE/DELETE).
- Cadena hash de eventos y verificacion de integridad.
- Compatibilidad con eventos legacy sin hash.
- Deteccion de manipulacion por inserciones forjadas.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

# Agregar src al path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.data_access import GestorTickets


@pytest.fixture
def gestor_tmp(tmp_path):
    """Instancia aislada de GestorTickets sobre DB temporal."""
    db_path = tmp_path / "tickets_test.db"
    return GestorTickets(db_path=db_path)


def _crear_ticket_base(db: GestorTickets) -> str:
    ticket = db.crear_ticket(
        usuario_ad="tester",
        hostname="PC-TEST",
        mac_address="AA:BB:CC:DD:EE:99",
        categoria="Hardware",
        descripcion="Fallo de prueba",
        prioridad="Alta",
        incluir_detalle_respuesta=False,
    )
    return ticket["ID_TICKET"]


def test_ticket_log_es_inmutable_update_delete(gestor_tmp):
    """No debe permitir UPDATE/DELETE sobre ticket_log por triggers."""
    id_ticket = _crear_ticket_base(gestor_tmp)

    # Hay al menos un registro por la creacion de ticket.
    rows = gestor_tmp._consultar("SELECT ID FROM ticket_log WHERE ID_TICKET=?", (id_ticket,))
    assert rows
    row_id = rows[0]["ID"]

    conn = gestor_tmp._c()

    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE ticket_log SET DETALLE='alterado' WHERE ID=?", (row_id,))

    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM ticket_log WHERE ID=?", (row_id,))


def test_integridad_ok_con_cadena_hash_valida(gestor_tmp):
    """La verificacion debe devolver OK cuando la cadena es valida."""
    id_ticket = _crear_ticket_base(gestor_tmp)

    ok = gestor_tmp.actualizar_ticket(
        id_ticket,
        estado="En Proceso",
        usuario_op="operador.qa",
        origen="tests",
    )
    assert ok is True

    ok = gestor_tmp.actualizar_ticket(
        id_ticket,
        notas_resolucion="Diagnostico inicial",
        usuario_op="operador.qa",
        origen="tests",
    )
    assert ok is True

    res = gestor_tmp.verificar_integridad_log_ticket(id_ticket)
    assert res["ok"] is True
    assert res["total"] >= 3
    assert res["verificados"] >= 3
    assert res["errores"] == []


def test_integridad_detecta_evento_forjado(gestor_tmp):
    """Debe detectar mismatch si se inserta un evento manual con hash invalido."""
    id_ticket = _crear_ticket_base(gestor_tmp)

    # Insercion forjada (append-only) con hash inconsistente.
    gestor_tmp._ejecutar(
        """INSERT INTO ticket_log
           (ID_TICKET, FECHA, USUARIO_OP, ACCION, DETALLE, ORIGEN, ESTADO_ANTES, ESTADO_DESPUES, META_JSON, HASH_PREV, HASH_EVENT)
           VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            id_ticket,
            "intruso",
            "Evento forjado",
            "Insercion manual no firmada",
            "tests.forge",
            "Abierto",
            "En Proceso",
            "{}",
            "HASH_PREV_FALSO",
            "HASH_EVENT_FALSO",
        ),
    )

    res = gestor_tmp.verificar_integridad_log_ticket(id_ticket)
    assert res["ok"] is False
    assert len(res["errores"]) >= 1


def test_legacy_sin_hash_no_rompe_verificacion(gestor_tmp):
    """Eventos legacy (sin hash) deben contarse como legacy, sin romper."""
    id_ticket = _crear_ticket_base(gestor_tmp)

    # Insert legacy sin HASH_EVENT para simular registros previos a la mejora.
    gestor_tmp._ejecutar(
        """INSERT INTO ticket_log
           (ID_TICKET, FECHA, USUARIO_OP, ACCION, DETALLE, ORIGEN)
           VALUES (?, datetime('now'), ?, ?, ?, ?)""",
        (id_ticket, "legacy.user", "Legacy", "Evento sin hash", "legacy.import"),
    )

    res = gestor_tmp.verificar_integridad_log_ticket(id_ticket)
    assert res["legacy"] >= 1
    # Puede quedar ok=True si no hay eventos corruptos.
    assert "ok" in res
    assert "total" in res


def test_log_incluye_transicion_estado_y_origen(gestor_tmp):
    """Los eventos nuevos deben traer ORIGEN y traza de estado."""
    id_ticket = _crear_ticket_base(gestor_tmp)

    ok = gestor_tmp.actualizar_ticket(
        id_ticket,
        estado="En Proceso",
        usuario_op="auditor.user",
        origen="tests.transition",
    )
    assert ok is True

    entradas = gestor_tmp.obtener_log_ticket(id_ticket)
    assert len(entradas) >= 2

    # Buscar el ultimo cambio de estado registrado.
    cambio_estado = next((e for e in entradas if e.get("ACCION") == "Cambio de estado"), None)
    assert cambio_estado is not None
    assert cambio_estado.get("ORIGEN") == "tests.transition"
    assert cambio_estado.get("ESTADO_ANTES") == "Abierto"
    assert cambio_estado.get("ESTADO_DESPUES") == "En Proceso"
