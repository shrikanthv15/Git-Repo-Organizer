import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal.activities import (
    analyze_repo_health,
    create_pull_request_activity,
    fetch_repo_list_activity,
    generate_readme_activity,
    get_repo_context_activity,
    say_hello,
)
from app.temporal.workflows import (
    AnalysisWorkflow,
    BatchGardeningWorkflow,
    GreetingWorkflow,
    JanitorWorkflow,
)

TASK_QUEUE = "gardener-queue"


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            GreetingWorkflow,
            AnalysisWorkflow,
            BatchGardeningWorkflow,
            JanitorWorkflow,
        ],
        activities=[
            say_hello,
            analyze_repo_health,
            fetch_repo_list_activity,
            get_repo_context_activity,
            generate_readme_activity,
            create_pull_request_activity,
        ],
    )

    print(f"Worker started, listening on queue: {TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
