import asyncio
import random
from app.logger import setup_logger

logger = setup_logger("resilience")


class DownstreamServiceError(Exception):
    """Raised when downstream dependency fails."""
    pass


async def call_downstream_dependency(
    simulated_failure_rate: float = 0.0,
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 1.0,
) -> int:
    """Simulates a call to a downstream service with exponential backoff and jitter.

    Returns the number of attempts made.
    """
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        # Random simulated failure check
        if random.random() < simulated_failure_rate:
            if attempts >= max_retries:
                logger.error(
                    "Downstream dependency exhausted all retries",
                    extra={"attempts": attempts, "max_retries": max_retries},
                )
                raise DownstreamServiceError(
                    f"Downstream service unavailable after {attempts} attempts"
                )

            # Exponential backoff with full jitter
            delay = min(max_delay, base_delay * (2 ** (attempts - 1)))
            jittered_delay = delay * (0.5 + random.random() * 0.5)
            logger.warning(
                "Downstream dependency failed, retrying...",
                extra={"attempt": attempts, "retry_delay": round(jittered_delay, 3)},
            )
            await asyncio.sleep(jittered_delay)
        else:
            logger.info("Downstream dependency call succeeded", extra={"attempt": attempts})
            return attempts

    return attempts
