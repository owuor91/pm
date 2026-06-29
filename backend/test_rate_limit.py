from backend import rate_limit


def setup_function():
    rate_limit._state.clear()


def test_not_locked_out_before_threshold():
    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS - 1):
        rate_limit.record_failure("alice", now=0)
    assert not rate_limit.is_locked_out("alice", now=0)


def test_locked_out_after_threshold():
    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
        rate_limit.record_failure("alice", now=0)
    assert rate_limit.is_locked_out("alice", now=0)


def test_lockout_expires_after_window():
    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
        rate_limit.record_failure("alice", now=0)
    assert rate_limit.is_locked_out("alice", now=rate_limit.LOCKOUT_SECONDS - 1)
    assert not rate_limit.is_locked_out("alice", now=rate_limit.LOCKOUT_SECONDS + 1)


def test_reset_clears_lockout():
    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
        rate_limit.record_failure("alice", now=0)
    rate_limit.reset("alice")
    assert not rate_limit.is_locked_out("alice", now=0)


def test_failures_are_tracked_per_key():
    for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
        rate_limit.record_failure("alice", now=0)
    assert rate_limit.is_locked_out("alice", now=0)
    assert not rate_limit.is_locked_out("bob", now=0)
