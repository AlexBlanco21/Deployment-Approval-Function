# vsdp-automate-deployment-approvals

Azure Function para automatizar la validación de aprobaciones de despliegue en **GitHub Actions**. Esta función valida que los despliegues sean iniciados únicamente por usuarios autorizados.

## 🎯 Funcionalidad

Esta Azure Function recibe webhooks de GitHub Actions cuando se requiere una aprobación para un environment y:

1. **Valida el usuario**: Verifica que el usuario que inició el workflow sea `APZW3PRD_BCP` (configurable)
2. **Rechaza despliegues no autorizados**: Si el usuario no está autorizado:
   - Rechaza la ejecución automáticamente
   - Registra un error en el resumen del workflow
   - Envía un mensaje: `"El usuario utilizado para el despliegue no se encuentra autorizado para desplegar en {ENV name}"`
3. **Aprueba despliegues autorizados**: Si el usuario está autorizado, aprueba automáticamente el despliegue

## 📋 Requisitos Previos

- Python 3.9 o superior
- Azure Functions Core Tools v4.x
- Una organización o repositorio de GitHub
- Un GitHub Personal Access Token o GitHub App con los siguientes permisos:
  - **Actions**: Read & Write
  - **Deployments**: Write
  - **Workflows**: Read
  - **Contents**: Read

## 🚀 Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone https://github.com/YOUR_ORG/vsdp-automate-deployment-approvals.git
cd vsdp-automate-deployment-approvals
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

Edita el archivo `local.settings.json` con tus valores:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "GITHUB_TOKEN": "ghp_tu_token_aqui_o_ghs_token_de_github_app",
    "GITHUB_WEBHOOK_SECRET": "tu_secreto_webhook",
    "AUTHORIZED_USER": "APZW3PRD_BCP"
  }
}
```

**Nota**: En producción, usa Azure Key Vault para almacenar el token de forma segura.

### 4. Ejecutar Localmente

```bash
func start
```

La función estará disponible en: `http://localhost:7071/api/approval-webhook`

## ☁️ Despliegue en Azure

### Opción 1: Usando Azure CLI

```bash
# Crear un Resource Group
az group create --name rg-approval-automation --location eastus

# Crear una Storage Account
az storage account create \
  --name stapprovalautomation \
  --resource-group rg-approval-automation \
  --location eastus \
  --sku Standard_LRS

# Crear la Function App
az functionapp create \
  --name func-approval-automation \
  --resource-group rg-approval-automation \
  --storage-account stapprovalautomation \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --os-type Linux

# Configurar variables de entorno
az functionapp config appsettings set \
  --name func-approval-automation \
  --resource-group rg-approval-automation \
  --settings \
    GITHUB_TOKEN="tu-github-token" \
    GITHUB_WEBHOOK_SECRET="tu-secreto" \
    AUTHORIZED_USER="APZW3PRD_BCP"

# Desplegar el código
func azure functionapp publish func-approval-automation
```

### Opción 2: Usando VS Code

1. Instala la extensión "Azure Functions" en VS Code
2. Inicia sesión en tu cuenta de Azure
3. Haz clic derecho en la carpeta del proyecto
4. Selecciona "Deploy to Function App..."
5. Sigue las instrucciones para crear o seleccionar una Function App

## 🔗 Configurar Deployment Protection Rule en GitHub

### Paso 1: Obtener la URL del Webhook

Después del despliegue, obtén la URL de la función:

```bash
# Obtener la URL base
az functionapp show \
  --name func-approval-automation \
  --resource-group rg-approval-automation \
  --query "defaultHostName" -o tsv

# Obtener el function key
az functionapp function keys list \
  --name func-approval-automation \
  --resource-group rg-approval-automation \
  --function-name ApprovalWebhook \
  --query "default" -o tsv
```

La URL será algo como:
```
https://func-approval-automation.azurewebsites.net/api/approval-webhook?code=FUNCTION_KEY
```

### Paso 2: Crear una GitHub App (Recomendado)

Para usar Deployment Protection Rules, necesitas una GitHub App:

1. Ve a **Settings** → **Developer settings** → **GitHub Apps**
2. Haz clic en **New GitHub App**
3. Configura:
   - **GitHub App name**: Deployment Approval Validator
   - **Homepage URL**: URL de tu organización
   - **Webhook URL**: La URL de tu Azure Function
   - **Webhook secret**: Un secreto seguro (guárdalo en `GITHUB_WEBHOOK_SECRET`)
4. En **Repository permissions**:
   - **Actions**: Read & Write
   - **Deployments**: Write
   - **Contents**: Read
5. En **Subscribe to events**:
   - Marca **Deployment protection rule**
6. Haz clic en **Create GitHub App**
7. Genera y descarga la private key
8. Anota el **App ID** y **Client ID**

### Paso 3: Instalar la GitHub App

1. Ve a la página de tu GitHub App
2. Haz clic en **Install App**
3. Selecciona la organización o repositorio donde quieres instalarla
4. Confirma la instalación

### Paso 4: Configurar el Environment con Deployment Protection

1. Ve a tu repositorio en GitHub
2. Navega a **Settings** → **Environments**
3. Selecciona o crea un environment (ej: "Production")
4. En **Deployment protection rules**, haz clic en **Enable deployment protection rules**
5. Selecciona tu GitHub App instalada
6. Guarda los cambios

## 📁 Estructura del Proyecto

```
vsdp-automate-deployment-approvals/
├── ApprovalWebhook/
│   └── function.json              # Configuración del trigger HTTP
├── shared/
│   ├── __init__.py
│   ├── github_client.py           # Cliente para GitHub API
│   └── approval_validator.py      # Lógica de validación de usuarios
├── function_app.py                 # Función principal del webhook
├── host.json                       # Configuración del host de Azure Functions
├── local.settings.json            # Configuración local (no incluir en git)
├── requirements.txt               # Dependencias de Python
├── .gitignore
├── README.md
├── EXAMPLE_PAYLOAD.md             # Ejemplos de payloads de GitHub
└── GITHUB_WORKFLOW.md             # Ejemplos de workflows
```

## 🧪 Pruebas

### Probar con un Webhook de Ejemplo

Puedes probar la función con un payload de ejemplo usando `curl`:

```bash
curl -X POST http://localhost:7071/api/approval-webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: deployment_protection_rule" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d @test-payload.json
```

Ver [EXAMPLE_PAYLOAD.md](EXAMPLE_PAYLOAD.md) para ejemplos completos de payloads.

## 📊 Monitoreo y Logs

### Ver Logs en Tiempo Real

```bash
func azure functionapp logstream func-approval-automation
```

### Ver Logs en Azure Portal

1. Ve a tu Function App en Azure Portal
2. Navega a **Monitor** → **Logs**
3. Puedes ver todas las invocaciones y sus resultados

### Application Insights

Para habilitar Application Insights:

```bash
az monitor app-insights component create \
  --app ai-approval-automation \
  --resource-group rg-approval-automation \
  --location eastus

# Obtener la instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app ai-approval-automation \
  --resource-group rg-approval-automation \
  --query "instrumentationKey" -o tsv)

az functionapp config appsettings set \
  --name func-approval-automation \
  --resource-group rg-approval-automation \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="$INSTRUMENTATION_KEY"
```

## 🔒 Seguridad

### Mejores Prácticas

1. **Usa Azure Key Vault** para almacenar el token de GitHub:
   ```bash
   # Crear Key Vault
   az keyvault create \
     --name kv-approval-automation \
     --resource-group rg-approval-automation \
     --location eastus
   
   # Almacenar el token
   az keyvault secret set \
     --vault-name kv-approval-automation \
     --name "GitHubToken" \
     --value "tu-token"
   
   # Habilitar Managed Identity en la Function App
   az functionapp identity assign \
     --name func-approval-automation \
     --resource-group rg-approval-automation
   
   # Obtener el principal ID
   PRINCIPAL_ID=$(az functionapp identity show \
     --name func-approval-automation \
     --resource-group rg-approval-automation \
     --query principalId -o tsv)
   
   # Dar acceso a la Function App
   az keyvault set-policy \
     --name kv-approval-automation \
     --object-id $PRINCIPAL_ID \
     --secret-permissions get
   ```

2. **Verifica las firmas de webhook**:
   - La función incluye verificación de firma HMAC-SHA256
   - Configura `GITHUB_WEBHOOK_SECRET` para habilitar la verificación

3. **Limita el acceso a la Function**:
   - Usa la autenticación de nivel de función (Function Key)
   - Considera usar Azure Private Link para acceso privado
   - Habilita HTTPS únicamente

4. **Auditoría**:
   - Todos los rechazos se registran en los logs
   - Usa Application Insights para análisis de tendencias

## 🛠️ Solución de Problemas

### La función no se activa
- Verifica que la GitHub App esté correctamente instalada
- Comprueba que la URL del webhook sea correcta
- Revisa los logs de GitHub en Settings → Developer settings → GitHub Apps → [Tu App] → Advanced

### Rechazos incorrectos
- Verifica que el nombre de usuario en `AUTHORIZED_USER` sea exacto (es el login de GitHub)
- Revisa los logs para ver qué usuario se detectó
- La comparación es case-insensitive

### Errores de autenticación con GitHub
- Verifica que el token sea válido y no haya expirado
- Confirma que el token tenga los permisos necesarios
- Para GitHub App, verifica que tenga los permisos correctos instalados

### Firma de webhook inválida
- Verifica que `GITHUB_WEBHOOK_SECRET` coincida con el secreto configurado en la GitHub App
- Asegúrate de que el header `X-Hub-Signature-256` esté presente

## 📝 Variables de GitHub Disponibles en el Webhook

El webhook de GitHub incluye estas variables importantes:

- `github.actor`: Usuario que disparó el workflow
- `github.triggering_actor`: Usuario que inició la ejecución
- `deployment.environment`: Nombre del environment
- `repository.full_name`: Nombre completo del repositorio
- `workflow.id`: ID del workflow run

Ver [EXAMPLE_PAYLOAD.md](EXAMPLE_PAYLOAD.md) para la estructura completa.

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para preguntas o problemas:
- Abre un issue en GitHub
- Contacta al equipo de DevOps

## 🔄 Changelog

### v1.0.0 (2026-01-27)
- ✨ Versión inicial para GitHub Actions
- ✅ Validación de usuarios autorizados
- ✅ Rechazo/Aprobación automática de despliegues
- ✅ Integración con GitHub deployment protection rules
- ✅ Verificación de firma de webhook
- ✅ Soporte para GitHub Apps
