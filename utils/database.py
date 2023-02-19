import psycopg2
import pandas as pd


def select(table):
    query = f"SELECT * FROM {table}"

    connection = psycopg2.connect(host='127.0.0.1', database='manitobabot', user='postgres', password='postgres')
    result = pd.read_sql(query, connection).sort_values(by="id", ignore_index=True)
    connection.close()
    return result


def delete(table, id):
    query = f"""DELETE FROM {table}
            WHERE id = {id}
            RETURNING *;"""
    connection = psycopg2.connect(host='127.0.0.1', database='manitobabot', user='postgres', password='postgres')
    result = pd.read_sql(query, connection)
    connection.commit()
    connection.close()
    return result


def insert_data(id, nombre):
    query = f"""INSERT INTO data
                (id,nombre)
                VALUES ({id},'{nombre}');"""

    connect(query)


def update_data1(data):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE data
        SET ultimo_mensaje='{data.ultimo_mensaje}', total_mensajes={data.total_mensajes}, sticker={data.sticker}, gif={data.gif}
        WHERE id={data.id};"""
    connect(query)


def update_data2(id, nombre, apellidos, apodo, genero, cumple, cumple_ano):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE data
        SET nombre='{nombre}', apellidos='{apellidos}', apodo='{apodo}', genero='{genero}', cumple='{cumple}', cumple_ano={cumple_ano}
        WHERE id={id};"""
    connect(query)


def insert_conversacion(id, mensaje_id, nombre):
    query = f"""INSERT INTO conversaciones
                (id, mensaje_id,nombre, total_mensajes)
                VALUES ({id},{mensaje_id},'{nombre}',{0});"""

    connect(query)


def update_conversacion(conversacion):
    query = f"""
        UPDATE  conversaciones
        SET
            total_mensajes ={conversacion.total_mensajes},
            mensaje_id = {conversacion.mensaje_id}
        WHERE id={conversacion.id};"""
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


def insert_lista(lista):
    query = f"""set DateStyle='ISO, DMY';
        INSERT INTO listas
        (nombre, elementos, tipo_elementos, fecha, creador, id_mensaje)
        VALUES ( '{lista.nombre}', ARRAY{lista.elementos}, ARRAY{list(map(int, lista.tipo_elementos))}, '{lista.fecha}',{lista.creador}, {lista.id_mensaje});"""
    connect(query)


def update_lista(lista):
    query = f"""set DateStyle='ISO, DMY';
        UPDATE listas
        SET (nombre, elementos, tipo_elementos, fecha, creador, id_mensaje) =
        ( '{lista.nombre}', ARRAY{lista.elementos}, ARRAY{list(map(int, lista.tipo_elementos))}, '{lista.fecha}',{lista.creador}, {lista.id_mensaje})
        WHERE id = {lista.id};"""
    connect(query)


def insert_bote(persona, cantidad, total, motivo):
    query = f"""set DateStyle='ISO, DMY';
    INSERT INTO botes
        (persona, cantidad, total, motivo)
         VALUES ({persona}, {cantidad}, {total}, '{motivo}');"""

    connect(query)


def insert_gastos(id, motivo, cantidad, fecha, nombre):
    query = f"""set DateStyle='ISO, DMY';
    INSERT INTO gastos    
    (id_persona, motivo, cantidad, fecha, nombre_persona)
         VALUES ({id}, '{motivo}', {cantidad}, '{fecha}', '{nombre}');"""

    connect(query)


def update_gasto(id_gasto):
    query = f"""
        UPDATE gastos
        SET pagado = True
        WHERE id = {id_gasto};"""
    connect(query)


def update_cumple(id_persona, cancion, idioma, sticker):
    query = f"""
        UPDATE data
        SET cumple_song = '{cancion}', cumple_lang='{idioma}', cumple_sticker='{sticker}'
        WHERE id = {id_persona};"""
    connect(query)


def insert_poll(id, question, options, votes, url, chat_id, message_id):
    query = f"""set DateStyle='ISO, DMY';
    INSERT INTO encuestas    
    (id, question, options, votes, url,chat_id,message_id)
         VALUES ({id}, '{question}', ARRAY{options},ARRAY{votes}::integer[], '{url}',{chat_id},{message_id});"""
    connect(query)


def update_poll(id, votes, message_id):
    query = f"""
        UPDATE encuestas
        SET votes = ARRAY{votes}::bigint[], message_id={message_id}
        WHERE id = {id};"""
    connect(query)


def end_poll(id):
    query = f"""
        UPDATE encuestas
        SET "end" = true
        WHERE id = {id};"""
    connect(query)


def connect(query):
    connection = psycopg2.connect(host='127.0.0.1', database='manitobabot', user='postgres', password='postgres')
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()
    connection.close()
