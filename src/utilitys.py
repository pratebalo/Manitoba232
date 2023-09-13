from utils import database as db


def get_person(person_id: int):
    data = db.select('data')
    person = data[data.id == person_id].squeeze()

    return person


def set_actual_user(person_id: int, context):
    person = get_person(person_id)
    context.user_data["user"] = person
