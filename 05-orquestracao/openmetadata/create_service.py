import os

from metadata.generated.schema.api.services.createDatabaseService import (
    CreateDatabaseServiceRequest,
)
from metadata.generated.schema.entity.services.connections.database.customDatabaseConnection import (
    CustomDatabaseConnection,
    CustomDatabaseType,
)
from metadata.generated.schema.entity.services.databaseService import (
    DatabaseConnection,
    DatabaseService,
    DatabaseServiceType,
)
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider,
    OpenMetadataConnection,
)
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.ingestion.ometa.ometa_api import OpenMetadata

from om_auth import get_bot_jwt_token

SERVICE_NAME = 'duckdb_atividade4'
HOST_PORT = os.environ.get('OPENMETADATA_HOST_PORT', 'http://openmetadata-server:8585/api')
JWT_TOKEN = get_bot_jwt_token()


def main() -> None:
    server_config = OpenMetadataConnection(
        hostPort=HOST_PORT,
        authProvider=AuthProvider.openmetadata,
        securityConfig=OpenMetadataJWTClientConfig(jwtToken=JWT_TOKEN),
    )
    metadata = OpenMetadata(server_config)

    existing = metadata.get_by_name(entity=DatabaseService, fqn=SERVICE_NAME)
    if existing:
        print(f"Servico '{SERVICE_NAME}' ja existe no OpenMetadata, nada a fazer.")
        return

    create_request = CreateDatabaseServiceRequest(
        name=SERVICE_NAME,
        serviceType=DatabaseServiceType.CustomDatabase,
        connection=DatabaseConnection(
            config=CustomDatabaseConnection(
                type=CustomDatabaseType.CustomDatabase,
                sourcePythonClass='metadata.ingestion.source.database.customdatabase.source.CustomDatabaseSource',
            )
        ),
        description=('Camadas trusted/delivery da Atividade 4 (dbt + DuckDB). Sem conexao ao vivo: metadados vem dos artefatos do dbt.'),
    )
    metadata.create_or_update(create_request)
    print(f"Servico '{SERVICE_NAME}' criado no OpenMetadata.")


if __name__ == '__main__':
    main()
