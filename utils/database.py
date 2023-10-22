from utils.logger_config import logger
import pandas as pd
import numpy as np
import json

from decouple import config
from sqlalchemy import create_engine, text

HOST = config("HOST")
USER_DB = config("USER_DB")
DATABASE = config("DATABASE")
PASSWORD_DB = config("PASSWORD_DB")
engine = create_engine(f'postgresql://{USER_DB}:{PASSWORD_DB}@{HOST}/{DATABASE}')
connection = engine.connect()


def select(table):
    query = text(f"SELECT * FROM {table}")
    result = pd.read_sql(query, engine).sort_values(by="id", ignore_index=True)
    return result


def delete(table, idx):
    query = text(f"""DELETE FROM {table}
            WHERE id = {idx}
            RETURNING *;""")
    result = pd.read_sql(query, connection)
    connection.commit()

    return result


def insert_data(idx, name):
    query = text(f"""INSERT INTO data
                (id,nombre)
                VALUES ({idx},'{name}');""")

    connect(query)


def format_value(val):
    match val:
        case str():
            return "'{}'".format(val)
        case int() | float() | np.int64():
            return str(val)
        case bool():
            return 'TRUE' if val else 'FALSE'
        case None:
            return 'NULL'
        case list():
            return "ARRAY{}".format(val)
        case _:
            raise ValueError("Tipo de dato no soportado: {}".format(type(val)))


def update_fields_table(table, idx, **fields):
    query = text(f"""set DateStyle='ISO, DMY';
        UPDATE {table}
        SET {", ".join([f"{field} = {format_value(value)}" for field, value in fields.items()])}
        WHERE id = {idx}
        RETURNING *;""")
    return connect(query)


def insert_into_table(fields, values, table):
    query = text(f"""set DateStyle='ISO, DMY';
    INSERT INTO {table}
    ({", ".join(fields)})
     VALUES ({", ".join(list(map(format_value, values)))})
    RETURNING *;""")
    return connect(query)


def select_where(table, clauses, values):
    query = text(f"""SELECT * FROM {table} 
    WHERE {" AND ".join([f"{field} = {format_value(value)}" for field, value in zip(clauses, values)])} """)
    result = pd.read_sql(query, engine).sort_values(by="id", ignore_index=True)
    return result


def update_bot_activated_all():
    query = text(f"""set DateStyle='ISO, DMY';
        UPDATE data
        SET activado=True;""")
    connect(query)


def insert_tarea(tarea):
    query = text(f"""set DateStyle='ISO, DMY';
        INSERT INTO tareas
        (descripcion, personas, fecha, creador)
        VALUES ( '{tarea.descripcion}', ARRAY{list(map(int, tarea.personas))}, '{tarea.fecha}',{tarea.creador});""")
    connect(query)


def update_tarea(tarea):
    query = text(f"""set DateStyle='ISO, DMY';
        UPDATE tareas
        SET(descripcion, personas, fecha, creador, completada) =
        ( '{tarea.descripcion}', ARRAY{list(map(int, tarea.personas))}, '{tarea.fecha}',{tarea.creador},{tarea.completada})
        WHERE id = {tarea.id};""")
    connect(query)


def insert_list(my_list):
    query = text(f"""set DateStyle='ISO, DMY';
        INSERT INTO lists
        (list_name, elements, type_list, date, creator, message_id)
        VALUES ( '{my_list.list_name}', ARRAY{my_list.elements}, '{my_list.type_list}', '{my_list.date}',{my_list.creator}, {my_list.message_id})
        RETURNING *;""")
    return connect(query)


def update_list(my_list):
    query = text(f"""set DateStyle='ISO, DMY';
        UPDATE lists
        SET (list_name, elements, type_list, date, creator, message_id) =
        ( '{my_list.list_name}', ARRAY{my_list.elements}, '{my_list.type_list}', '{my_list.date}',{my_list.creator}, {my_list.message_id})
        WHERE id = {my_list.id};""")
    return connect(query)


def insert_bote(persona, cantidad, total, motivo):
    query = text(f"""set DateStyle='ISO, DMY';
    INSERT INTO botes
        (persona, cantidad, total, motivo)
         VALUES ({persona}, {cantidad}, {total}, '{motivo}')
    RETURNING *;""")

    return connect(query)


def insert_expense(id_expense, concept, price, date, photo):
    query = text(f"""set DateStyle='ISO, DMY';
    INSERT INTO expenses    
    (id_person, concept, paid, price, date, photo)
         VALUES ({id_expense}, '{concept}',FALSE, {price}, '{date}', {photo})
    RETURNING *;""")

    return connect(query)


def update_birth(id_person, song, language, sticker):
    query = text(f"""
        UPDATE data
        SET cumple_song = '{song}', cumple_lang='{language}', cumple_sticker='{sticker}'
        WHERE id = {id_person};""")
    connect(query)


def insert_poll(id_poll, question, options, votes, url, message_id):
    query = text(f"""set DateStyle='ISO, DMY';
    INSERT INTO encuestas    
    (id, question, options, votes, url,message_id)
         VALUES ({id_poll}, '{question}', ARRAY{options},ARRAY{votes}::integer[], '{url}',{message_id})
    RETURNING *;""")
    return connect(query)


def update_poll(idx, votes, message_id, last_vote):
    query = text(f"""
        UPDATE encuestas
        SET votes = ARRAY{votes}::bigint[], message_id={message_id}, last_vote='{json.dumps(last_vote)}'
        WHERE id = {idx};""")
    connect(query)


def connect(query):
    try:
        result = connection.execute(query)
        if result.returns_rows:
            if result.rowcount == 1:
                df = pd.Series(result.fetchall()[0], index=result.keys())
            else:
                df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
        else:
            df = None
    except Exception as e:
        connection.rollback()
        logger.error(f"Error: {e}")
        return None
    else:
        connection.commit()
        return df
    finally:
        connection.close()
