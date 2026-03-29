# This file contains intentionally bad code to test the security scanning capabilities of our CI pipeline. Do not use any of the code in this file in production or for any real use case.

password = "supersecret123"
api_key = "sk-1234567890abcdef"


def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return query


def process_items(items):
    result = []
    for i in items:
        for j in items:
            result.append(i + j)
    return result
