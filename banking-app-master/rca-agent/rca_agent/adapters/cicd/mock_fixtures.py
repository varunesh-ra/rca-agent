from datetime import datetime, timezone
from ...models import DeploymentRecord

MOCK_DEPLOYMENTS: dict[str, list[DeploymentRecord]] = {
    "payment-service": [
        DeploymentRecord(
            service_name="payment-service",
            environment="production",
            github_repo="payment-service",
            branch="main",
            commit_sha="REPLACE_WITH_REAL_SHA_AFTER_GIT_INIT",
            commit_message="perf: streamline charge_card hot path",
            deployed_at=datetime(2026, 5, 13, 10, 32, tzinfo=timezone.utc),
            deployer="jane.doe",
            pipeline_id="run-8821",
            pipeline_url="https://ci.internal/runs/8821",
            status="success",
        )
    ],
    "order-service": [
        DeploymentRecord(
            service_name="order-service",
            environment="production",
            github_repo="order-service",
            branch="main",
            commit_sha="REPLACE_WITH_REAL_SHA_AFTER_GIT_INIT",
            commit_message="chore: upgrade dependencies, pydantic to v2",
            deployed_at=datetime(2026, 5, 13, 9, 15, tzinfo=timezone.utc),
            deployer="bob.smith",
            pipeline_id="run-8819",
            pipeline_url="https://ci.internal/runs/8819",
            status="success",
        )
    ],
    "notification-service": [
        DeploymentRecord(
            service_name="notification-service",
            environment="staging",
            github_repo=None,  # intentionally absent — forces sub-agent discovery
            branch="main",
            commit_sha="REPLACE_WITH_REAL_SHA_AFTER_GIT_INIT",
            commit_message="refactor: simplify env var access",
            deployed_at=datetime(2026, 5, 13, 8, 0, tzinfo=timezone.utc),
            deployer="alice.chen",
            pipeline_id="run-8815",
            pipeline_url="https://ci.internal/runs/8815",
            status="success",
        )
    ],
}
