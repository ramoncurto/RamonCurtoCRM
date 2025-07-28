# 📱 WhatsApp Integration Setup Guide

## 🔍 Estado Actual

El sistema está funcionando correctamente pero las credenciales de WhatsApp no están configuradas. Esto es normal y esperado.

### ✅ Lo que funciona actualmente:
- Los mensajes se guardan en la base de datos
- El sistema intenta enviar por WhatsApp (Twilio o Meta)
- Si WhatsApp no está configurado, guarda el mensaje como respaldo
- Feedback claro al usuario sobre el estado del envío

### ⚠️ Lo que necesitas configurar:
- **Opción 1:** Credenciales de Twilio WhatsApp
- **Opción 2:** Credenciales de Meta WhatsApp Business API

---

## 🚀 Configuración de WhatsApp

### Opción 1: Twilio WhatsApp (Recomendado)

#### Paso 1: Crear Cuenta de Twilio
1. **Ir a:** https://www.twilio.com/
2. **Crear cuenta** gratuita
3. **Verificar número de teléfono** para WhatsApp

#### Paso 2: Obtener Credenciales de Twilio
1. **Account SID:** En Dashboard → "Account Info"
2. **Auth Token:** En Dashboard → "Account Info"
3. **WhatsApp Number:** Tu número verificado en Twilio

#### Paso 3: Configurar Variables de Entorno
```bash
# Windows (PowerShell)
$env:TWILIO_ACCOUNT_SID="tu_account_sid_aqui"
$env:TWILIO_AUTH_TOKEN="tu_auth_token_aqui"
$env:TWILIO_WHATSAPP_NUMBER="+1234567890"

# Windows (Command Prompt)
set TWILIO_ACCOUNT_SID=tu_account_sid_aqui
set TWILIO_AUTH_TOKEN=tu_auth_token_aqui
set TWILIO_WHATSAPP_NUMBER=+1234567890

# Linux/Mac
export TWILIO_ACCOUNT_SID="tu_account_sid_aqui"
export TWILIO_AUTH_TOKEN="tu_auth_token_aqui"
export TWILIO_WHATSAPP_NUMBER="+1234567890"
```

#### Paso 4: Verificar Dependencias
```bash
# El sistema usa httpx que ya está instalado
# No se requiere instalar la librería de Twilio
```

---

### Opción 2: Meta WhatsApp Business API

#### Paso 1: Crear Cuenta de Meta for Developers
1. **Ir a:** https://developers.facebook.com/
2. **Crear cuenta** o iniciar sesión
3. **Crear una nueva app** → "Business" → "WhatsApp"

#### Paso 2: Configurar WhatsApp Business API
1. **En tu app de Meta:**
   - Ir a "Products" → "WhatsApp" → "Getting Started"
   - Agregar número de teléfono
   - Verificar número con código SMS

2. **Obtener credenciales:**
   - **Phone ID:** En "WhatsApp" → "API Setup" → "Phone number ID"
   - **Access Token:** En "WhatsApp" → "API Setup" → "Access token"

#### Paso 3: Configurar Variables de Entorno
```bash
# Windows (PowerShell)
$env:WHATSAPP_PHONE_ID="tu_phone_id_aqui"
$env:WHATSAPP_ACCESS_TOKEN="tu_access_token_aqui"

# Windows (Command Prompt)
set WHATSAPP_PHONE_ID=tu_phone_id_aqui
set WHATSAPP_ACCESS_TOKEN=tu_access_token_aqui

# Linux/Mac
export WHATSAPP_PHONE_ID="tu_phone_id_aqui"
export WHATSAPP_ACCESS_TOKEN="tu_access_token_aqui"
```

---

### Configuración con Archivo .env (Recomendado)
```bash
# Crear archivo .env en la raíz del proyecto
# Para Twilio:
echo "TWILIO_ACCOUNT_SID=tu_account_sid_aqui" > .env
echo "TWILIO_AUTH_TOKEN=tu_auth_token_aqui" >> .env
echo "TWILIO_WHATSAPP_NUMBER=+1234567890" >> .env

# O para Meta:
echo "WHATSAPP_PHONE_ID=tu_phone_id_aqui" > .env
echo "WHATSAPP_ACCESS_TOKEN=tu_access_token_aqui" >> .env
```

---

## 🧪 Verificación de Configuración

### 1. Verificar Variables de Entorno
```bash
# Verificar configuración de Twilio
python -c "import os; print('TWILIO_ACCOUNT_SID:', os.getenv('TWILIO_ACCOUNT_SID', 'No configurado')); print('TWILIO_AUTH_TOKEN:', os.getenv('TWILIO_AUTH_TOKEN', 'No configurado')[:20] + '...' if os.getenv('TWILIO_AUTH_TOKEN') else 'No configurado'); print('TWILIO_WHATSAPP_NUMBER:', os.getenv('TWILIO_WHATSAPP_NUMBER', 'No configurado'))"

# Verificar configuración de Meta
python -c "import os; print('WHATSAPP_PHONE_ID:', os.getenv('WHATSAPP_PHONE_ID', 'No configurado')); print('WHATSAPP_ACCESS_TOKEN:', os.getenv('WHATSAPP_ACCESS_TOKEN', 'No configurado')[:20] + '...' if os.getenv('WHATSAPP_ACCESS_TOKEN') else 'No configurado')"
```

### 2. Endpoint de Prueba
```bash
# Acceder al endpoint de prueba
curl http://localhost:8000/test/whatsapp-config
```

**Respuesta esperada si Twilio está configurado:**
```json
{
    "twilio": {
        "configured": true,
        "account_sid": "AC1234567...",
        "auth_token": "abc123def...",
        "whatsapp_number": "+1234567890"
    },
    "meta": {
        "configured": false,
        "phone_id": null,
        "access_token": null
    },
    "system_status": "working",
    "message": "WhatsApp configured (Twilio or Meta)",
    "test_send_result": {
        "status": "sent",
        "data": {"sid": "MG1234567890..."}
    }
}
```

**Respuesta esperada si Meta está configurado:**
```json
{
    "twilio": {
        "configured": false,
        "account_sid": null,
        "auth_token": null,
        "whatsapp_number": null
    },
    "meta": {
        "configured": true,
        "phone_id": "1234567890...",
        "access_token": "EAAGH..."
    },
    "system_status": "working",
    "message": "WhatsApp configured (Twilio or Meta)",
    "test_send_result": {
        "status": "sent",
        "data": {...}
    }
}
```

**Respuesta actual (no configurado):**
```json
{
    "twilio": {
        "configured": false,
        "account_sid": null,
        "auth_token": null,
        "whatsapp_number": null
    },
    "meta": {
        "configured": false,
        "phone_id": null,
        "access_token": null
    },
    "system_status": "limited",
    "message": "WhatsApp not configured - messages will be saved to database",
    "test_send_result": {
        "status": "skipped",
        "message": "No WhatsApp credentials configured"
    }
}
```

---

## 📱 Flujo de Funcionamiento

### Con WhatsApp Configurado:
1. **Usuario envía mensaje** → Communication Hub
2. **Sistema detecta teléfono** → Atleta tiene número
3. **Intenta envío WhatsApp** → API de Meta
4. **Respuesta exitosa** → "Message sent via WhatsApp to [Nombre]"
5. **Mensaje guardado** → Base de datos como respaldo

### Sin WhatsApp Configurado (Estado Actual):
1. **Usuario envía mensaje** → Communication Hub
2. **Sistema detecta teléfono** → Atleta tiene número
3. **Intenta envío WhatsApp** → Credenciales no configuradas
4. **Guarda mensaje** → Base de datos
5. **Respuesta al usuario** → "Message saved (WhatsApp not configured)"

---

## 🔧 Configuración Rápida para Pruebas

### Opción 1: Configuración Temporal
```bash
# En la terminal donde ejecutas el servidor
$env:WHATSAPP_PHONE_ID="tu_phone_id"
$env:WHATSAPP_ACCESS_TOKEN="tu_access_token"
python start_server.py
```

### Opción 2: Archivo .env
```bash
# Crear archivo .env
echo "WHATSAPP_PHONE_ID=tu_phone_id" > .env
echo "WHATSAPP_ACCESS_TOKEN=tu_access_token" >> .env

# El servidor cargará automáticamente las variables
python start_server.py
```

### Opción 3: Modificar start_server.py
```python
# Agregar al inicio de start_server.py
import os
os.environ['WHATSAPP_PHONE_ID'] = 'tu_phone_id'
os.environ['WHATSAPP_ACCESS_TOKEN'] = 'tu_access_token'
```

---

## 🎯 Beneficios de Configurar WhatsApp

### ✅ Con WhatsApp Configurado:
- **Envío real** de mensajes a atletas
- **Respuestas automáticas** desde webhooks
- **Integración completa** con Meta Business API
- **Trazabilidad** de mensajes enviados/recibidos
- **Escalabilidad** para múltiples atletas

### ⚠️ Sin WhatsApp Configurado:
- **Mensajes guardados** en base de datos
- **Sin envío real** a atletas
- **Funcionalidad limitada** de comunicación
- **Dependencia** de otras plataformas

---

## 🚨 Troubleshooting

### Error: "Invalid phone number"
- Verificar formato del número: `+34679795648`
- Asegurar que el número esté verificado en Meta

### Error: "Invalid access token"
- Verificar que el token sea válido
- Regenerar token si es necesario

### Error: "Phone number not found"
- Verificar que el número esté registrado en WhatsApp Business
- Comprobar que el número esté verificado

### Warning: "No se configuraron credenciales"
- **Este es el estado actual** - es normal
- Configurar variables de entorno según la guía

---

## 📞 Próximos Pasos

1. **Configurar credenciales** de WhatsApp Business API
2. **Verificar configuración** con endpoint de prueba
3. **Probar envío** de mensaje desde communication hub
4. **Configurar webhook** para recibir mensajes entrantes
5. **Implementar email** como plataforma alternativa

---

## 🔗 Recursos Útiles

- [Meta for Developers](https://developers.facebook.com/)
- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp)
- [Graph API Reference](https://developers.facebook.com/docs/graph-api)
- [WhatsApp Business Platform](https://business.whatsapp.com/)

---

**Nota:** El sistema funciona correctamente incluso sin WhatsApp configurado. Los mensajes se guardan en la base de datos y el usuario recibe feedback claro sobre el estado del envío. 