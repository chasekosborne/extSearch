from clients.fit.db.submissions import create_fit_submission


def create_submission(user_id, shapes_payload):
    print("Creating rectangle submission for user_id:", user_id)
    return create_fit_submission(user_id, shapes_payload)
