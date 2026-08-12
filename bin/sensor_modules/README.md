# Sensor Module Management Tool

Manage sensor gateway application modules across deployment environments (LOCAL, ALPHA, BETA, PROD).

## Standard Workflow: From Update to Sensor Deployment

### 1. Build & Package

Build the sensor gateway application and package as ZIP:

```bash
# Build sensor application
# (build steps vary by environment)

# Create module ZIP
# Contents: compiled application binary + dependencies
zip sensor_01030506.zip -r app/
```

### 2. Upload to Server

Upload the new module to the target environment server:

```bash
cat sensor_01030506.zip | ./post.sh ALPHA
```

stderr output: `Module uploaded successfully` or error message.

### 3. Verify Upload

List all modules to confirm the new version is registered:

```bash
./list.sh ALPHA
```

stdout: JSON array of all available modules. Verify your new module ID appears in the list.

### 4. Automatic Sensor Update

When sensors start up, they automatically:
1. Contact the server's `/api/v1/modules` endpoint
2. Download the latest module for their configuration
3. Execute the new application

No manual action needed on the sensor side.

### 5. Download for Local Testing (Optional)

To test a module locally before deploying to sensors:

```bash
./get.sh ALPHA sensor_01030505 > sensor_01030505.zip
unzip sensor_01030505.zip -d ./test_module/
# Test the module locally
```

## Setup

Credentials are pre-filled in `.env.*` files. No setup needed unless passwords change.

Each file structure:
```
LOGIN_USER=factory                                           # do not change
LOGIN_PASSWORD=<password>                                   # factory account password
AUTH_BASE=https://mmw-{ENV}-apim.azure-api.net/auth        # authentication endpoint
API_BASE=https://mmw-{ENV}-apim.azure-api.net/manage       # modules management endpoint
SENSOR_BASE=https://mmw-{ENV}-apim.azure-api.net/sensor    # modules download endpoint
```

## Usage

### List available modules in an environment

```bash
./list.sh <ENV>
```

Example:
```bash
./list.sh ALPHA
```

Output: JSON list of all available modules with metadata (moduleId, version, createdAt, etc.).

### Download a specific module

```bash
./get.sh <ENV> <moduleId> > <output.zip>
```

Example:
```bash
./get.sh ALPHA sensor_01030505 > sensor_01030505.zip
```

Output: Binary module zip file written to stdout.

### Upload a new module

```bash
cat <module.zip> | ./post.sh <ENV> <moduleType> <version> [sensorId] [chipType]
```

Examples:
```bash
# Upload sensor module
cat sensor_01030506.zip | ./post.sh ALPHA sensor 01030506

# Upload config module for specific sensor
cat config.zip | ./post.sh ALPHA config 23 sensor_123

# Upload with chipType
cat module.zip | ./post.sh ALPHA sensor 01030506 "" "STM32"
```

Parameters:
- `<ENV>` — Target environment (LOCAL, ALPHA, BETA, PROD)
- `<moduleType>` — Module type: "sensor", "config", or "other"
- `<version>` — Module version (e.g., 01030506, 23)
- `[sensorId]` — Optional, sensor ID (for config modules)
- `[chipType]` — Optional, chip type

Output: Success message to stderr, or error details.

## Environments

| ENV   | AUTH_BASE | API_BASE | SENSOR_BASE |
|-------|-----------|----------|-------------|
| LOCAL | http://localhost:8080 | http://localhost:8080 | http://localhost:8080 |
| ALPHA | https://mmw-alpha-apim.azure-api.net/auth | https://mmw-alpha-apim.azure-api.net/manage | https://mmw-alpha-apim.azure-api.net/sensor |
| BETA  | https://mmw-beta-apim.azure-api.net/auth | https://mmw-beta-apim.azure-api.net/manage | https://mmw-beta-apim.azure-api.net/sensor |
| PROD  | https://mmw-prod-apim.azure-api.net/auth | https://mmw-prod-apim.azure-api.net/manage | https://mmw-prod-apim.azure-api.net/sensor |

## API Endpoints

All operations use JWT Bearer token authentication (obtained via factory user login).

### Authentication
- `POST /api/v1/login` — Login and get sessionToken

### Module Management (Api.Manage)
- `GET /api/v1/modules` — List all available modules
- `POST /api/v1/modules` — Upload new module (multipart/form-data)

### Module Download (Api.Sensor)
- `GET /api/v1/modules/{moduleId}` — Download specific module binary

## Authentication Flow

1. POST `AUTH_BASE/api/v1/login` with `{ customerId: "system", userId: "factory", password: "..." }`
2. Receive JWT `sessionToken` in response
3. Include `Authorization: Bearer <sessionToken>` in all subsequent requests
