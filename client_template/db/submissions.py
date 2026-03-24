from shared.db import get_cursor


def create_submission(user_id, payload):
    raise NotImplementedError("Implement create_submission for your problem.")


def get_submission(submission_id):
    raise NotImplementedError("Implement get_submission for your problem.")


def validate_submission(submission_id):
    raise NotImplementedError("Implement validate_submission for your problem.")
