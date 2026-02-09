import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.temporal.activities import (
    analyze_codebase_activity,
    analyze_repo_health,
    create_docs_pull_request_activity,
    create_or_update_profile_repo_activity,
    create_pull_request_activity,
    deep_scan_repo,
    fetch_repo_list_activity,
    fetch_repos_extended_activity,
    generate_deep_readme_activity,
    generate_doc_activity,
    generate_profile_readme_activity,
    generate_readme_activity,
    get_repo_context_activity,
    portfolio_deep_scan_activity,
    save_draft_proposal_activity,
    set_repo_status_activity,
    say_hello,
)
from app.temporal.workflows import (
    AnalysisWorkflow,
    BatchGardeningWorkflow,
    GreetingWorkflow,
    JanitorWorkflow,
    PortfolioWorkflow,
)

TASK_QUEUE = "gardener-queue"


async def main():
    client = await Client.connect(settings.TEMPORAL_ADDRESS)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            GreetingWorkflow,
            AnalysisWorkflow,
            BatchGardeningWorkflow,
            JanitorWorkflow,
            PortfolioWorkflow,
        ],
        activities=[
            say_hello,
            analyze_repo_health,
            analyze_codebase_activity,
            deep_scan_repo,
            fetch_repo_list_activity,
            fetch_repos_extended_activity,
            get_repo_context_activity,
            generate_readme_activity,
            generate_deep_readme_activity,
            generate_doc_activity,
            generate_profile_readme_activity,
            portfolio_deep_scan_activity,
            create_pull_request_activity,
            create_docs_pull_request_activity,
            create_or_update_profile_repo_activity,
            save_draft_proposal_activity,
            set_repo_status_activity,
        ],
    )

    logger.info("Worker started, listening on queue: %s", TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
