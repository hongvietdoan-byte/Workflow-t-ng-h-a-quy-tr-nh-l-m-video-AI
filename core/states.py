from enum import Enum


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYABLE = "retryable"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


TRANSITIONS = {
    JobState.QUEUED: {JobState.RUNNING, JobState.CANCELLED},
    JobState.RUNNING: {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED},
    JobState.FAILED: {JobState.RETRYABLE},
    JobState.RETRYABLE: {JobState.QUEUED, JobState.CANCELLED},
    JobState.SUCCEEDED: {JobState.PENDING_REVIEW, JobState.APPROVED, JobState.REJECTED},
    JobState.PENDING_REVIEW: {JobState.APPROVED, JobState.REJECTED},
    JobState.APPROVED: set(),
    JobState.REJECTED: set(),
    JobState.CANCELLED: set(),
}

REVIEWABLE = {JobState.SUCCEEDED, JobState.PENDING_REVIEW}


class InvalidTransition(Exception):
    pass


def check_transition(current: JobState, new: JobState) -> None:
    if new not in TRANSITIONS[current]:
        raise InvalidTransition(f"{current.value} -> {new.value} is not allowed")
