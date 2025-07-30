#!/usr/bin/env python3
"""
Script de diagnóstico para el sistema de transcripción
Verifica la configuración y funcionalidad de audio
"""

import os
import sys
import subprocess
import tempfile
import asyncio
from pathlib import Path
from transcription_service import transcription_service

def check_environment():
    """Verificar variables de entorno"""
    print("🔍 Verificando configuración del entorno...")
    
    # Check .env file
    env_file = Path('.env')
    if env_file.exists():
        print("✅ Archivo .env encontrado")
        
        # Check OpenAI API Key
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            if len(openai_key) > 20:
                masked_key = openai_key[:8] + "..." + openai_key[-4:]
                print(f"✅ OPENAI_API_KEY configurada: {masked_key}")
            else:
                print("⚠️  OPENAI_API_KEY parece ser muy corta")
        else:
            print("❌ OPENAI_API_KEY no encontrada en variables de entorno")
    else:
        print("⚠️  Archivo .env no encontrado")
    
    print()

def check_ffmpeg():
    """Verificar instalación de FFmpeg"""
    print("🔍 Verificando FFmpeg...")
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Extract version info
            lines = result.stdout.split('\n')
            version_line = lines[0] if lines else "Unknown version"
            print(f"✅ FFmpeg instalado: {version_line}")
            
            # Check for common codecs
            codecs_to_check = ['opus', 'vorbis', 'aac', 'mp3']
            print("   Codecs soportados:")
            
            for codec in codecs_to_check:
                codec_result = subprocess.run(
                    ['ffmpeg', '-codecs'], 
                    capture_output=True, 
                    text=True,
                    timeout=5
                )
                if codec in codec_result.stdout.lower():
                    print(f"   ✅ {codec.upper()}")
                else:
                    print(f"   ❌ {codec.upper()}")
        else:
            print("❌ FFmpeg instalado pero no funciona correctamente")
            print(f"   Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg no responde (timeout)")
    except FileNotFoundError:
        print("❌ FFmpeg no está instalado")
        print("💡 Instrucciones de instalación:")
        print("   Windows: Descargar de https://ffmpeg.org/download.html")
        print("   macOS: brew install ffmpeg")
        print("   Linux: sudo apt install ffmpeg")
    except Exception as e:
        print(f"❌ Error verificando FFmpeg: {e}")
    
    print()

def check_transcription_service():
    """Verificar el servicio de transcripción"""
    print("🔍 Verificando servicio de transcripción...")
    
    status = transcription_service.get_system_status()
    
    print(f"   OpenAI configurado: {'✅' if status['openai_api_configured'] else '❌'}")
    print(f"   FFmpeg disponible: {'✅' if status['ffmpeg_available'] else '❌'}")
    
    print("   Formatos soportados directamente:")
    for fmt in status['supported_direct_formats']:
        print(f"     ✅ {fmt}")
    
    if status['ffmpeg_available']:
        print("   Formatos soportados con conversión:")
        for fmt in status['supported_conversion_formats']:
            print(f"     🔄 {fmt}")
    
    if status['recommendations']:
        print("   Recomendaciones:")
        for rec in status['recommendations']:
            icon = {"error": "❌", "warning": "⚠️", "success": "✅"}.get(rec['type'], "ℹ️")
            print(f"     {icon} {rec['message']}")
            print(f"        💡 {rec['action']}")
    
    print()

def create_test_audio_files():
    """Crear archivos de audio de prueba para testing"""
    print("🔍 Creando archivos de audio de prueba...")
    
    test_dir = Path('test_audio')
    test_dir.mkdir(exist_ok=True)
    
    # Generate a simple sine wave test audio (1 second, 440Hz)
    try:
        # Create a 1-second WAV file with FFmpeg
        wav_file = test_dir / 'test_voice.wav'
        
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', 'sine=frequency=440:duration=1',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            str(wav_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ Archivo de prueba WAV creado: {wav_file}")
            
            # Convert to other formats for testing
            formats_to_test = [
                ('ogg', ['-c:a', 'libopus']),
                ('m4a', ['-c:a', 'aac']),
            ]
            
            for ext, codec_args in formats_to_test:
                output_file = test_dir / f'test_voice.{ext}'
                convert_cmd = [
                    'ffmpeg',
                    '-i', str(wav_file),
                    *codec_args,
                    '-y',
                    str(output_file)
                ]
                
                convert_result = subprocess.run(convert_cmd, capture_output=True, timeout=30)
                if convert_result.returncode == 0:
                    print(f"✅ Archivo de prueba {ext.upper()} creado: {output_file}")
                else:
                    print(f"❌ Error creando archivo {ext.upper()}")
        else:
            print("❌ Error creando archivo de prueba WAV")
            
    except Exception as e:
        print(f"❌ Error creando archivos de prueba: {e}")
    
    print()
    return test_dir

async def test_transcription():
    """Probar la funcionalidad de transcripción"""
    print("🔍 Probando transcripción...")
    
    # Test with a simple text-to-speech if available
    test_dir = Path('test_audio')
    
    if not test_dir.exists():
        print("❌ No hay archivos de prueba disponibles")
        return
    
    # Find test files
    test_files = list(test_dir.glob('test_voice.*'))
    
    if not test_files:
        print("❌ No se encontraron archivos de prueba")
        return
    
    for test_file in test_files:
        print(f"   Probando {test_file.name}...")
        
        try:
            result = await transcription_service.transcribe_audio(str(test_file))
            
            if result and not result.startswith('❌'):
                print(f"   ✅ Transcripción exitosa: {len(result)} characters")
                if len(result) < 100:
                    print(f"      Resultado: {result}")
                else:
                    print(f"      Resultado: {result[:100]}...")
            else:
                print(f"   ❌ Error en transcripción: {result}")
                
        except Exception as e:
            print(f"   ❌ Excepción durante transcripción: {e}")
    
    print()

def check_common_whatsapp_issues():
    """Verificar problemas comunes con WhatsApp"""
    print("🔍 Verificando configuración para WhatsApp/Telegram...")
    
    # Check uploads directory
    uploads_dir = Path('uploads')
    if uploads_dir.exists():
        print("✅ Directorio uploads existe")
        
        # Check for .opus files (common WhatsApp format)
        opus_files = list(uploads_dir.glob('*.opus'))
        ogg_files = list(uploads_dir.glob('*.ogg'))
        
        if opus_files:
            print(f"   📁 Encontrados {len(opus_files)} archivos .opus")
        if ogg_files:
            print(f"   📁 Encontrados {len(ogg_files)} archivos .ogg")
            
        if opus_files or ogg_files:
            print("   💡 Estos formatos requieren FFmpeg para conversión")
    else:
        print("⚠️  Directorio uploads no existe")
    
    # Check file upload limits
    print("   Límites de archivos:")
    print("     ✅ OpenAI Whisper: máximo 25MB")
    print("     💡 WhatsApp voice: típicamente <1MB")
    print("     💡 Telegram voice: típicamente <20MB")
    
    print()

def show_usage_examples():
    """Mostrar ejemplos de uso"""
    print("💡 Ejemplos de uso:")
    print()
    
    print("1. Subir audio desde WhatsApp:")
    print("   - Formato típico: .ogg (codec OPUS)")
    print("   - Requiere FFmpeg para conversión")
    print("   - Tamaño típico: 10KB - 1MB")
    print()
    
    print("2. Subir audio desde Telegram:")
    print("   - Formato típico: .ogg o .m4a")
    print("   - Requiere FFmpeg para algunos formatos")
    print("   - Tamaño típico: 50KB - 20MB")
    print()
    
    print("3. Formatos directamente soportados:")
    print("   - .mp3, .wav, .flac, .mp4")
    print("   - No requieren conversión")
    print("   - Procesamiento más rápido")
    print()

async def main():
    """Función principal de diagnóstico"""
    print("🏥 DIAGNÓSTICO DEL SISTEMA DE TRANSCRIPCIÓN")
    print("=" * 50)
    print()
    
    # Run all diagnostic checks
    check_environment()
    check_ffmpeg()
    check_transcription_service()
    
    # Create test files if FFmpeg is available
    if transcription_service.ffmpeg_available:
        test_dir = create_test_audio_files()
        await test_transcription()
    else:
        print("⚠️  Saltando pruebas de transcripción (FFmpeg no disponible)")
        print()
    
    check_common_whatsapp_issues()
    show_usage_examples()
    
    # Final summary
    print("📋 RESUMEN:")
    print("=" * 20)
    
    status = transcription_service.get_system_status()
    
    if status['openai_api_configured'] and status['ffmpeg_available']:
        print("✅ Sistema completamente funcional")
        print("   - Todos los formatos de audio soportados")
        print("   - WhatsApp/Telegram completamente compatibles")
    elif status['openai_api_configured']:
        print("⚠️  Sistema parcialmente funcional")
        print("   - OpenAI Whisper configurado")
        print("   - Solo formatos básicos soportados (.mp3, .wav)")
        print("   - Instalar FFmpeg para soporte completo")
    else:
        print("❌ Sistema no funcional")
        print("   - Configurar OPENAI_API_KEY")
        if not status['ffmpeg_available']:
            print("   - Instalar FFmpeg")
    
    print()
    print("🔗 Enlaces útiles:")
    print("   OpenAI API: https://platform.openai.com/account/api-keys")
    print("   FFmpeg: https://ffmpeg.org/download.html")
    print("   Documentación: README.md")

if __name__ == "__main__":
    asyncio.run(main())