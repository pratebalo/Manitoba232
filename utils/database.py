import psycopg2
import pandas as pd
import json

from decouple import config

HOST = config("HOST")


def select(table):
    query = f"SELECT * FROM {table}"

    connection = psycopg2.connect(host=HOST, database='manitobabot', user='postgres', password='postgres')
    result = pd.read_sql(query, connection).sort_values(by="id", ignore_index=True)
    connection.close()
    return result


def delete(table, idx):
    query = f"""DELETE FROM {table}
            WHERE id = {idx}
            RETURNING *;"""
    connection = psycopg2.connect(host=HOST, database='manitobabot', user='postgres', password='postgres')
    result = pd.read_sql(query, connection)
    connection.commit()
    connection.close()
    return result


def insert_data(idx, name):
    query = f"""INSERT INTO data
                (id,nombre)
                VALUES ({idx},'{name}');"""

    connect(query)


def update_data_messages(data):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE data
        SET ultimo_mensaje='{data.ultimo_mensaje}', total_mensajes={data.total_mensajes},
        ronda_mensajes={data.ronda_mensajes}, sticker={data.sticker}, gif={data.gif}
        WHERE id={data.id};"""
    connect(query)


def update_data_start(idx, name, surname, nick, gender, birth, birth_year):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE data
        SET nombre='{name}', apellidos='{surname}', apodo='{nick}', genero='{gender}', cumple='{birth}', cumple_ano={birth_year}
        WHERE id={idx};"""
    connect(query)


def format_value(val):
    if isinstance(val, str):
        return "'{}'".format(val)
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, bool):
        return 'TRUE' if val else 'FALSE'
    elif val is None:
        return 'NULL'
    elif isinstance(val, list):
        return "ARRAY{}".format(val)
    else:
        raise ValueError("Tipo de dato no soportado: {}".format(type(val)))


def update_field_table(idx, fields, values, table):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE {table}
        SET {", ".join([f"{field} = {format_value(value)}" for field, value in zip(fields, values)])}
        WHERE id = {idx};
        """
    connect(query)


def update_bot_activated_all():
    query = f"""set DateStyle='ISO, DMY';
        UPDATE data
        SET activado=True;"""
    connect(query)


def update_bot_not_activated(idx):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE data
        SET activado=False
        WHERE id={idx};"""
    connect(query)


def insert_tarea(tarea):
    query = f"""set DateStyle='ISO, DMY';
        INSERT INTO tareas
        (descripcion, personas, fecha, creador)
        VALUES ( '{tarea.descripcion}', ARRAY{list(map(int, tarea.personas))}, '{tarea.fecha}',{tarea.creador});"""
    connect(query)


def update_tarea(tarea):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE tareas
        SET(descripcion, personas, fecha, creador, completada) =
        ( '{tarea.descripcion}', ARRAY{list(map(int, tarea.personas))}, '{tarea.fecha}',{tarea.creador},{tarea.completada})
        WHERE id = {tarea.id};"""
    connect(query)


def insert_list(lista):
    query = f"""set DateStyle='ISO, DMY';
        INSERT INTO listas
        (nombre, elementos, tipo_elementos, fecha, creador, id_mensaje)
        VALUES ( '{lista.nombre}', ARRAY{lista.elementos}, ARRAY{list(map(int, lista.tipo_elementos))}, '{lista.fecha}',{lista.creador}, {lista.id_mensaje});"""
    connect(query)


def update_list(lista):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE listas
        SET (nombre, elementos, tipo_elementos, fecha, creador, id_mensaje) =
        ( '{lista.nombre}', ARRAY{lista.elementos}, ARRAY{lista(map(int, lista.tipo_elementos))}, '{lista.fecha}',{lista.creador}, {lista.id_mensaje})
        WHERE id = {lista.id};"""
    connect(query)


def insert_bote(persona, cantidad, total, motivo):
    query = f"""set DateStyle='ISO, DMY';
    INSERT INTO botes
        (persona, cantidad, total, motivo)
         VALUES ({persona}, {cantidad}, {total}, '{motivo}');"""

    connect(query)


def insert_expense(id_expense, concept, price, date, photo):
    query = f"""set DateStyle='ISO, DMY';
    INSERT INTO expenses    
    (id_person, concept, paid, price, date, photo)
         VALUES ({id_expense}, '{concept}',FALSE, {price}, '{date}', {photo})
    RETURNING id;"""

    return connect(query)


def update_expense_paid(id_expense):
    query = f"""
        UPDATE expenses
        SET paid = True
        WHERE id = {id_expense};"""
    connect(query)


def update_expense_file(id_expense, id_file):
    query = f"""
        UPDATE expenses
        SET id_file = '{id_file}'
        WHERE id = {id_expense};"""
    connect(query)


def update_birth(id_person, song, language, sticker):
    query = f"""
        UPDATE data
        SET cumple_song = '{song}', cumple_lang='{language}', cumple_sticker='{sticker}'
        WHERE id = {id_person};"""
    connect(query)


def insert_poll(id_poll, question, options, votes, url, chat_id, message_id):
    query = f"""set DateStyle='ISO, DMY';
    INSERT INTO encuestas    
    (id, question, options, votes, url,chat_id,message_id)
         VALUES ({id_poll}, '{question}', ARRAY{options},ARRAY{votes}::integer[], '{url}',{chat_id},{message_id});"""
    connect(query)


def update_poll(idx, votes, message_id, last_vote):
    query = f"""
        UPDATE encuestas
        SET votes = ARRAY{votes}::bigint[], message_id={message_id}, last_vote='{json.dumps(last_vote)}'
        WHERE id = {idx};"""
    connect(query)


def end_poll(idx):
    query = f"""
        UPDATE encuestas
        SET "end" = true
        WHERE id = {idx};"""
    connect(query)


def connect(query):
    connection = psycopg2.connect(host=HOST, database='manitobabot', user='postgres', password='postgres')
    cursor = connection.cursor()
    cursor.execute(query)
    if cursor.description:
        row = cursor.fetchone()[0]
    else:
        row = None
    connection.commit()
    cursor.close()
    connection.close()
    return row
