#!/usr/bin/env python3
"""
Script de migración: Sistema Antiguo → Sistema Workflow
Migra datos de tabla 'records' a nueva arquitectura unificada
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

def migrate_legacy_to_workflow(db_path: str = 'database.db'):
    """Migrar datos del sistema antiguo al nuevo workflow"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🚀 Iniciando migración Legacy → Workflow")
    
    # 1. Verificar que existen las tablas nuevas
    print("📋 Verificando esquema de base de datos...")
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            print("❌ Error: Tabla 'messages' no existe. Ejecuta init_workflow_db.py primero")
            return False
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'")
        if not cursor.fetchone():
            print("ℹ️  Tabla 'records' no existe. No hay datos que migrar.")
            return True
            
        print("✅ Esquema verificado")
        
    except Exception as e:
        print(f"❌ Error verificando esquema: {e}")
        return False
    
    # 2. Obtener datos de tabla records
    print("📊 Analizando datos existentes...")
    
    cursor.execute("SELECT COUNT(*) FROM records")
    records_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    messages_count = cursor.fetchone()[0]
    
    print(f"   Records existentes: {records_count}")
    print(f"   Messages existentes: {messages_count}")
    
    if records_count == 0:
        print("ℹ️  No hay records que migrar")
        return True
    
    # 3. Migrar records → messages + conversations
    print("🔄 Migrando records → messages...")
    
    # Obtener todos los records
    cursor.execute("""
        SELECT 
            id, athlete_id, filename, transcription, generated_response, 
            final_response, timestamp, category, notes, audio_duration
        FROM records 
        ORDER BY timestamp ASC
    """)
    
    records = cursor.fetchall()
    migrated_count = 0
    errors = []
    
    for record in records:
        try:
            record_id, athlete_id, filename, transcription, generated_response, final_response, timestamp, category, notes, audio_duration = record
            
            # Obtener o crear conversación para el atleta
            conversation_id = get_or_create_conversation(cursor, athlete_id)
            
            # Generar hash de deduplicación
            dedupe_content = f"legacy_migration:record_{record_id}:{athlete_id}"
            dedupe_hash = hashlib.sha256(dedupe_content.encode()).hexdigest()
            
            # Verificar si ya fue migrado
            cursor.execute("SELECT id FROM messages WHERE dedupe_hash = ?", (dedupe_hash,))
            if cursor.fetchone():
                print(f"   ⏭️  Record {record_id} ya migrado")
                continue
            
            # Preparar metadata
            metadata = {
                "migrated_from": "records",
                "original_record_id": record_id,
                "migration_date": datetime.now().isoformat(),
                "generated_response": generated_response,
                "category": category,
                "notes": notes
            }
            
            # Insertar mensaje
            cursor.execute("""
                INSERT INTO messages (
                    conversation_id, athlete_id, source_channel, source_message_id,
                    direction, content_text, content_audio_url, transcription,
                    generated_response, final_response, audio_duration,
                    metadata_json, dedupe_hash, filename, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                athlete_id,
                'legacy',  # source_channel
                f"record_{record_id}",  # source_message_id
                'in',  # direction
                None,  # content_text (estará en transcription)
                f"/uploads/{filename}" if filename else None,  # content_audio_url
                transcription,
                generated_response,
                final_response,
                audio_duration,
                json.dumps(metadata),
                dedupe_hash,
                filename,
                timestamp or datetime.now().isoformat()
            ))
            
            migrated_count += 1
            
            if migrated_count % 10 == 0:
                print(f"   📈 Migrados: {migrated_count}/{records_count}")
                
        except Exception as e:
            error_msg = f"Error migrando record {record_id}: {e}"
            errors.append(error_msg)
            print(f"   ❌ {error_msg}")
    
    # 4. Migrar highlights de athlete_highlights (si usa el sistema antiguo)
    print("🎯 Migrando highlights...")
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='athlete_highlights'")
        if cursor.fetchone():
            # Migrar highlights antiguos
            migrate_old_highlights(cursor)
        else:
            print("   ℹ️  No se encontró tabla athlete_highlights antigua")
    except Exception as e:
        print(f"   ⚠️  Error migrando highlights: {e}")
    
    # 5. Commit y resumen
    conn.commit()
    
    print("📊 Resumen de migración:")
    print(f"   ✅ Records migrados: {migrated_count}")
    print(f"   ❌ Errores: {len(errors)}")
    
    if errors:
        print("   📝 Errores detallados:")
        for error in errors[:5]:  # Mostrar máximo 5 errores
            print(f"      • {error}")
        if len(errors) > 5:
            print(f"      ... y {len(errors) - 5} errores más")
    
    # 6. Crear backup de tabla records
    if migrated_count > 0:
        print("💾 Creando backup de tabla records...")
        try:
            cursor.execute("ALTER TABLE records RENAME TO records_backup_legacy")
            print("   ✅ Tabla records renombrada a records_backup_legacy")
        except Exception as e:
            print(f"   ⚠️  Error creando backup: {e}")
    
    conn.close()
    
    print("🎉 Migración completada exitosamente!")
    return migrated_count > 0

def get_or_create_conversation(cursor, athlete_id: int) -> int:
    """Obtener o crear conversación para atleta"""
    
    # Buscar conversación existente
    cursor.execute("""
        SELECT id FROM conversations 
        WHERE athlete_id = ? 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (athlete_id,))
    
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Crear nueva conversación
    cursor.execute("""
        INSERT INTO conversations (athlete_id, topic, channel) 
        VALUES (?, 'Conversación migrada', 'legacy')
    """, (athlete_id,))
    
    return cursor.lastrowid

def migrate_old_highlights(cursor):
    """Migrar highlights del sistema antiguo al nuevo"""
    
    # Verificar si existen highlights antiguos
    cursor.execute("SELECT COUNT(*) FROM athlete_highlights")
    old_highlights_count = cursor.fetchone()[0]
    
    if old_highlights_count == 0:
        print("   ℹ️  No hay highlights antiguos que migrar")
        return
    
    print(f"   📊 Migrando {old_highlights_count} highlights...")
    
    # Obtener highlights antiguos
    cursor.execute("""
        SELECT 
            id, athlete_id, highlight_text, category, 
            source_conversation_id, is_active, created_at
        FROM athlete_highlights
    """)
    
    old_highlights = cursor.fetchall()
    migrated_highlights = 0
    
    for highlight in old_highlights:
        try:
            old_id, athlete_id, text, category, source_conversation_id, is_active, created_at = highlight
            
            # Buscar message_id correspondiente si source_conversation_id existe
            message_id = None
            if source_conversation_id:
                cursor.execute("""
                    SELECT id FROM messages 
                    WHERE metadata_json LIKE ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (f'%"original_record_id": {source_conversation_id}%',))
                
                result = cursor.fetchone()
                if result:
                    message_id = result[0]
            
            # Insertar en nueva tabla highlights
            cursor.execute("""
                INSERT INTO highlights (
                    athlete_id, message_id, highlight_text, category,
                    source, status, is_manual, is_active, created_at
                ) VALUES (?, ?, ?, ?, 'manual', 'accepted', 1, ?, ?)
            """, (
                athlete_id, message_id, text, category or 'other',
                1 if is_active else 0, created_at
            ))
            
            migrated_highlights += 1
            
        except Exception as e:
            print(f"      ❌ Error migrando highlight {old_id}: {e}")
    
    print(f"   ✅ Highlights migrados: {migrated_highlights}")
    
    # Renombrar tabla antigua
    try:
        cursor.execute("ALTER TABLE athlete_highlights RENAME TO athlete_highlights_backup_legacy")
        print("   ✅ Tabla athlete_highlights renombrada a backup")
    except Exception as e:
        print(f"   ⚠️  Error renombrando tabla highlights: {e}")

def verify_migration(db_path: str = 'database.db'):
    """Verificar que la migración fue exitosa"""
    
    print("🔍 Verificando migración...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Contar registros en cada tabla
        cursor.execute("SELECT COUNT(*) FROM messages WHERE source_channel = 'legacy'")
        migrated_messages = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM highlights")
        highlights = cursor.fetchone()[0]
        
        print(f"   📊 Mensajes migrados: {migrated_messages}")
        print(f"   📊 Conversaciones: {conversations}")
        print(f"   📊 Highlights: {highlights}")
        
        # Verificar que hay datos para cada atleta
        cursor.execute("""
            SELECT a.id, a.name, COUNT(m.id) as message_count
            FROM athletes a
            LEFT JOIN messages m ON a.id = m.athlete_id
            GROUP BY a.id, a.name
            ORDER BY message_count DESC
        """)
        
        athlete_stats = cursor.fetchall()
        
        print("   👥 Mensajes por atleta:")
        for athlete_id, name, count in athlete_stats[:5]:
            print(f"      • {name}: {count} mensajes")
        
        print("✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
    
    finally:
        conn.close()

def rollback_migration(db_path: str = 'database.db'):
    """Rollback de migración si algo sale mal"""
    
    print("🔄 Iniciando rollback de migración...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si existen las tablas backup
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records_backup_legacy'")
        if not cursor.fetchone():
            print("❌ No se encontró backup de records. No se puede hacer rollback.")
            return False
        
        # Eliminar datos migrados
        cursor.execute("DELETE FROM messages WHERE source_channel = 'legacy'")
        deleted_messages = cursor.rowcount
        
        cursor.execute("DELETE FROM highlights WHERE source = 'manual' AND is_manual = 1")
        deleted_highlights = cursor.rowcount
        
        # Restaurar tablas originales
        cursor.execute("ALTER TABLE records_backup_legacy RENAME TO records")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='athlete_highlights_backup_legacy'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE athlete_highlights_backup_legacy RENAME TO athlete_highlights")
        
        conn.commit()
        
        print(f"✅ Rollback completado:")
        print(f"   • {deleted_messages} mensajes eliminados")
        print(f"   • {deleted_highlights} highlights eliminados")
        print(f"   • Tablas originales restauradas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en rollback: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "verify":
            verify_migration()
        elif sys.argv[1] == "rollback":
            rollback_migration()
        else:
            print("Uso: python data_migration.py [verify|rollback]")
    else:
        # Migración normal
        success = migrate_legacy_to_workflow()
        
        if success:
            verify_migration()
            print("\n🎯 Siguiente paso: Actualizar workspace.js para usar nueva API")
        else:
            print("\n❌ Migración falló. Revisa los errores arriba.")