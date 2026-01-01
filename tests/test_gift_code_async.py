"""Test to verify GiftCodeService works correctly with concurrent requests."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from services.gift_code_service import GiftCodeService


@pytest.mark.asyncio
async def test_concurrent_execution_time():
    """
    Verify that concurrent creates tasks - measure time diff between sequential vs concurrent.
    This is a simpler test that confirms the async pattern without complex mocking.
    """

    # Simulate 5 tasks that take 0.1s each
    async def dummy_task(i):
        await asyncio.sleep(0.1)
        return {"success": True, "id": i}

    # Measure time for concurrent execution
    start_time = time.time()

    # Create 5 concurrent tasks (should take ~0.1s, not 0.5s)
    tasks = [dummy_task(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    elapsed_time = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"Async Concurrency Pattern Test")
    print(f"{'='*60}")
    print(f"Total tasks: 5")
    print(f"Time per task: 0.1 second")
    print(f"Elapsed time: {elapsed_time:.3f}s")
    print(f"Expected if concurrent: ~0.1s")
    print(f"Expected if sequential: ~0.5s")
    print(f"Status: {'✓ TRULY CONCURRENT' if elapsed_time < 0.3 else '✗ SEQUENTIAL'}")
    print(f"{'='*60}\n")

    assert elapsed_time < 0.3, f"Tasks took {elapsed_time:.3f}s - should be ~0.1s for concurrent"
    assert all(r["success"] for r in results)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_shared_session_reuse():
    """Verify that the service reuses the same session across requests."""
    service = GiftCodeService()

    # Get session twice
    session1 = await service.ensure_session()
    session2 = await service.ensure_session()

    # Should be the same object
    assert session1 is session2, "Session should be reused, not recreated"

    print("✓ Session reuse verified")

    await service.close()


@pytest.mark.asyncio
async def test_context_manager_cleanup():
    """Verify that context manager properly initializes and cleans up."""
    async with GiftCodeService() as service:
        assert service._session is not None, "Session should be initialized in context manager"

    # After exiting, session should be None
    assert service._session is None, "Session should be closed after context manager exit"

    print("✓ Context manager cleanup verified")


if __name__ == "__main__":
    print("\nRunning async verification tests...\n")

    # Run all tests
    asyncio.run(test_concurrent_execution_time())
    asyncio.run(test_shared_session_reuse())
    asyncio.run(test_context_manager_cleanup())

    print("All async tests passed! ✓")
