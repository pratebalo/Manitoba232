from utils.sheets_drive import spreadsheets, get_sheet, append_data, clear_sheet
import warnings
from utils.logger_config import logger
import pandas as pd
import src.utilitys as ut
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes
from decouple import config

MENU1, MENU2, CREAR_LISTA2, EDITAR_LISTA1, EDITAR_LISTA2, EDITAR_LISTA_A, EDITAR_LISTA_E, ELIMINAR_LISTA, FINAL_OPTION = range(9)
warnings.filterwarnings("ignore")

ID_MENU = config("ID_MENU")
ID_TESORERIA = config("ID_TESORERIA")

lista_comidas = ['Desayuno', 'Almuerzo', 'Comida', 'Merienda', 'Cena', 'Pan', 'Postre']
columnas_excluir = ['Recetas', 'Ingredientes', 'Medidas']


def letra_a_numero_columna(letra):
    """Convierte una letra de columna a su equivalente numérico."""
    if len(letra) == 1:
        return ord(letra.upper()) - ord('A') + 1
    elif len(letra) == 2:
        return (ord(letra.upper()[0]) - ord('A') + 1) * 26 + (ord(letra.upper()[1]) - ord('A') + 1)


def numero_a_letra_columna(numero):
    """Convierte un número de columna a su equivalente en letras."""
    if numero <= 26:
        return chr(ord('A') + numero - 1)
    else:
        primera_letra = chr(ord('A') + (numero - 1) // 26)
        segunda_letra = chr(ord('A') + (numero - 1) % 26)
        return f"{primera_letra}{segunda_letra}"


def suma_columna(letra, x):
    """Suma x al número de columna correspondiente a la letra."""
    numero_columna = letra_a_numero_columna(letra)
    nuevo_numero_columna = numero_columna + x
    nueva_letra_columna = numero_a_letra_columna(nuevo_numero_columna)
    return nueva_letra_columna


def get_recetarios():
    recetario_global = {}
    for comida in lista_comidas:
        x = spreadsheets.values().get(spreadsheetId=ID_MENU, range=f'{comida}!B1:P1000').execute()['values']
        headers = x.pop(0)
        data = pd.DataFrame(x, columns=headers).dropna(how='all')
        columnas_restantes = [col for col in data.columns if col not in columnas_excluir]

        data[columnas_restantes] = data[columnas_restantes].replace('', 0.0).fillna(0.0).astype(float)
        merges = spreadsheets.get(spreadsheetId=ID_MENU, ranges=f'{comida}!B1:K1000').execute()['sheets'][0]
        if 'merges' in merges:
            merges = merges['merges']
        else:
            merges = []
        merged = {}
        for i in merges:
            merged[i['startRowIndex'] - 1] = i['endRowIndex'] - 1
        recetario = {}
        recetas = list(filter(None, data.Recetas.unique().tolist()))
        for receta in recetas:
            pos = data.index[data.Recetas == receta].tolist()[0]
            if pos in merged:
                end = merged[pos]
            else:
                end = pos
            temp = data.loc[pos:end]
            recetario[receta] = temp.iloc[:, 0:3]
            recetario[receta].insert(3, 'Castores_Jefes', temp.Adultos)
            recetario[receta].insert(4, 'Castores_Gluten', temp.Gluten)
            recetario[receta].insert(5, 'Castores_Lactoso', temp.Lactoso)
            recetario[receta].insert(6, 'Castores_Vegie', temp.Vegie)
            recetario[receta].insert(7, 'Castores_Vegie_lact', temp.Vegie_lact)
            recetario[receta].insert(8, 'Manada', temp.Manada)
            recetario[receta].insert(9, 'Manada_Jefes', temp.Adultos)
            recetario[receta].insert(10, 'Manada_Gluten', temp.Gluten)
            recetario[receta].insert(11, 'Manada_Lactoso', temp.Lactoso)
            recetario[receta].insert(12, 'Manada_Vegie', temp.Vegie)
            recetario[receta].insert(13, 'Manada_Vegie_lact', temp.Vegie_lact)
            recetario[receta].insert(14, 'Tropa', temp.Tropa)
            recetario[receta].insert(15, 'Tropa_Jefes', temp.Adultos)
            recetario[receta].insert(16, 'Tropa_Gluten', temp.Gluten)
            recetario[receta].insert(17, 'Tropa_Lactoso', temp.Lactoso)
            recetario[receta].insert(18, 'Tropa_Vegie', temp.Vegie)
            recetario[receta].insert(19, 'Tropa_Vegie_lact', temp.Vegie_lact)
            recetario[receta].insert(20, 'Escultas', temp.Adultos)
            recetario[receta].insert(21, 'Escultas_Jefes', temp.Adultos)
            recetario[receta].insert(22, 'Escultas_Gluten', temp.Gluten)
            recetario[receta].insert(23, 'Escultas_Lactoso', temp.Lactoso)
            recetario[receta].insert(24, 'Escultas_Vegie', temp.Vegie)
            recetario[receta].insert(25, 'Escultas_Vegie_lact', temp.Vegie_lact)
            recetario[receta].insert(26, 'Rover', temp.Adultos)
            recetario[receta].insert(27, 'Rover_Jefes', temp.Adultos)
            recetario[receta].insert(28, 'Rover_Gluten', temp.Gluten)
            recetario[receta].insert(29, 'Rover_Lactoso', temp.Lactoso)
            recetario[receta].insert(30, 'Rover_Vegie', temp.Vegie)
            recetario[receta].insert(31, 'Rover_Vegie_lact', temp.Vegie_lact)
            recetario[receta].insert(32, 'Intendentes', temp.Adultos)
            recetario[receta].insert(33, 'Intendentes_Gluten', temp.Gluten)
            recetario[receta].insert(34, 'Intendentes_Lactoso', temp.Lactoso)
            recetario[receta].insert(35, 'Intendentes_Vegie', temp.Vegie)
            recetario[receta].insert(36, 'Intendentes_Vegie_lact', temp.Vegie_lact)
            recetario[receta].insert(37, 'Comun', temp.Comun)
            recetario[receta].insert(38, 'Medidas', temp.Medidas)

        recetario_global[comida] = recetario

    return recetario_global


maps = ["Castores", "Manada", "Tropa", "Escultas", "Rover"]


def get_acampadas():
    acampadas = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Menú_acampada!J4:N8').execute()['values']

    return [sorted([maps.index(valor) for valor in acampada]) for acampada in acampadas]


def get_menu_acampada():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Menú_acampada!B3:G11').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_menu_verano():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Menú_verano!A3:11').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_menu_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Menú_verano!A14:D19').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_fechas_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Menú_verano!G15:H19').execute()['values']
    lista_resultante = []

    for sublista in x:
        if int(sublista[1]) - int(sublista[0]) == 1:
            sublista.insert(1, '0')
            lista_intermedia = sublista
        else:
            lista_intermedia = [str(i) for i in range(int(sublista[0]), int(sublista[1]) + 1)]
        lista_resultante.append(lista_intermedia)
    return lista_resultante


def get_servicio():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Menú_verano!K15:M17').execute()['values']
    lista_resultante = [[x[0][0], str(int(x[0][0]) + 1)], [x[1][0], str(int(x[1][0]) + 1), int(x[1][1])],
                        [x[2][0], str(int(x[2][0]) + 1), str(int(x[2][0]) + 2), x[2][2]]]

    return lista_resultante


def get_cantidades_verano(menu, recetario, asistentes, marcha, servicio):
    cantidades = pd.DataFrame(
        columns=['Recetas', 'Ingredientes', 'TOTAL', 'Medidas', 'Castores', 'Manada', 'Intendentes',
                 'Total Intendencia',
                 'Tropa', 'Escultas', 'Rovers', 'Comun'])
    lista = {0: [0, 4],
             1: [4, 8],
             2: [8, 12],
             3: [12, 17],
             4: [17, 21]
             }
    last_day = None
    for day in menu:
        for comida in menu.index:
            if not menu.at[comida, day]:
                continue

            day_visitors = list(map(int, asistentes.loc[[day]].values.tolist()[0]))

            for ix_unidad, unidad in enumerate(marcha):
                if day in unidad:
                    ix = unidad.index(day)
                    match ix:
                        case 0:
                            if comida != 'Desayuno':
                                dias_marcha = lista[ix_unidad]
                                day_visitors[dias_marcha[0]:dias_marcha[1]] = [0] * (dias_marcha[1] - dias_marcha[0])

                        case 1:
                            dias_marcha = lista[ix_unidad]
                            day_visitors[dias_marcha[0]:dias_marcha[1]] = [0] * (dias_marcha[1] - dias_marcha[0])
                        case 2:
                            if comida != 'Cena' and comida != 'Pan_cena':
                                dias_marcha = lista[ix_unidad]
                                day_visitors[dias_marcha[0]:dias_marcha[1]] = [0] * (dias_marcha[1] - dias_marcha[0])

            # 24H
            if day in servicio[0][0] and comida != 'Desayuno' or day in servicio[0][1] and comida == 'Desayuno':
                day_visitors[lista[2][0]:lista[2][0] + 2] = [0] * 2

            # 24H scout
            if day in servicio[1][0] and comida != 'Desayuno' or day in servicio[1][1] and comida == 'Desayuno':
                day_visitors[lista[2][0]] = day_visitors[lista[2][0]] - servicio[1][2]

            if day in servicio[2][0] and comida != 'Desayuno' or day in servicio[2][1] or \
                    day in servicio[1][1] and comida == 'Desayuno':
                day_visitors[lista[3][0]:lista[3][0] + 2] = [0] * 2

            receta = menu.at[comida, day]
            if 'Pan' in comida:
                new = recetario['Pan'][receta].copy()
            else:
                new = recetario[comida][receta].copy()

            if day != last_day:
                day_visitors2 = [sum(day_visitors[0:21]), sum(day_visitors[0:4]), sum(day_visitors[4:8]),
                                 day_visitors[21], sum(day_visitors[0:8]) + day_visitors[19], sum(day_visitors[8:12]),
                                 sum(day_visitors[12:17]), sum(day_visitors[17:21])]
                last_day = day
                new_row = [f'Día {day}', '', day_visitors2[0]] + [''] + day_visitors2[1:] + ['']
                cantidades.loc[len(cantidades)] = new_row

            new.iloc[:, 2:24] = new.iloc[:, 2:24] * day_visitors
            new2 = pd.concat(
                [new.iloc[:, 0:2], new.iloc[:, 2:24].sum(axis=1), new.iloc[:, 25], new.iloc[:, 2:6].sum(axis=1),
                 new.iloc[:, 6:10].sum(axis=1), new.iloc[:, 23], new.iloc[:, 2:10].join(new.iloc[:, 23]).sum(axis=1),
                 new.iloc[:, 10:14].sum(axis=1), new.iloc[:, 14:19].sum(axis=1), new.iloc[:, 19:23].sum(axis=1),
                 new.iloc[:, 24]], axis=1)
            new2.columns = ['Recetas', 'Ingredientes', 'TOTAL', 'Medidas', 'Castores', 'Manada', 'Intendentes',
                            'Total Intendencia', 'Tropa', 'Escultas', 'Rovers', 'Comun']
            if comida in ['Desayuno', 'Almuerzo', 'Merienda', 'Pan_cena', 'Postre']:
                cantidades = pd.concat([cantidades, new2, pd.DataFrame([[]])]).reset_index(drop=True)
            else:
                cantidades = pd.concat([cantidades, new2]).reset_index(drop=True)

    cantidades = cantidades.fillna('').reset_index(drop=True)
    return cantidades


def get_cantidades_marcha(menu, recetario, asistentes, fechas):
    asistentes.drop(['Intendentes'], axis=1, inplace=True)
    cols = ['Recetas', 'Ingredientes', 'TOTAL', 'Medidas', 'Castores', 'Manada', 'Tropa', 'Escultas', 'Rovers', 'Comun']
    cantidades = pd.DataFrame(columns=cols)
    lista = {0: [0, 4],
             1: [4, 8],
             2: [8, 12],
             3: [12, 17],
             4: [17, 21]
             }
    last_day = None
    for day in menu:
        for comida in menu.index:
            if not menu.at[comida, day]:
                continue
            day_visitors = []
            for i in range(0, 5):
                if fechas[i][int(day) - 1] == '0':
                    day_visitors.extend([0, 0, 0, 0])
                else:
                    select = asistentes.loc[fechas[i][int(day) - 1]].tolist()[lista[i][0]:lista[i][1]]
                    day_visitors.extend(list(map(int, select)))
            if day != last_day:
                day_visitors2 = [sum(day_visitors[0:4]), sum(day_visitors[4:8]), sum(day_visitors[8:12]),
                                 sum(day_visitors[12:17]), sum(day_visitors[17:21])]
                last_day = day
                new_row = [f'Día {day}', '', ''] + day_visitors2 + ['', '']
                cantidades.loc[len(cantidades)] = new_row

            receta = menu.at[comida, day]
            new = recetario[comida][receta].copy().drop(['Intendentes'], axis=1)
            new.iloc[:, 2:23] = new.iloc[:, 2:23] * day_visitors
            new2 = pd.concat(
                [new.iloc[:, 0:2], new.iloc[:, 2:23].sum(axis=1), new.iloc[:, 24], new.iloc[:, 2:6].sum(axis=1),
                 new.iloc[:, 6:10].sum(axis=1), new.iloc[:, 10:14].sum(axis=1), new.iloc[:, 14:19].sum(axis=1),
                 new.iloc[:, 19:23].sum(axis=1), new.iloc[:, 23]], axis=1)
            new2.columns = cols

            cantidades = pd.concat([cantidades, new2, pd.DataFrame([[]])]).reset_index(drop=True)

    cantidades = cantidades.fillna('').reset_index(drop=True)
    return cantidades


def get_cantidades_acampada(menu, recetario, asistentes):
    acampadas = get_acampadas()
    all_cantidades = []
    for i, acampada in enumerate(acampadas):
        acampadas_original = [maps[valor] if isinstance(valor, int) else valor for valor in acampada]
        columns = ['Recetas', 'Ingredientes', f'TOTAL{i + 1}', 'Medidas'] + acampadas_original + ['Comun']
        cantidades = pd.DataFrame(columns=columns)
        positions = [indice * 6 + i for indice in acampada for i in range(6)]
        positions2 = [0, 1] + [2 + indice * 6 + i for indice in acampada for i in range(6)] + [-2, -1]
        last_day = None
        for day in menu:
            for comida in menu.index:
                if not menu.at[comida, day]:
                    continue

                all_day_visitors = list(map(int, asistentes.loc[[day]].values.tolist()[0]))
                day_visitors = [all_day_visitors[i] for i in positions]
                receta = menu.at[comida, day]
                if 'Pan' in comida:
                    new = recetario['Pan'][receta].copy().iloc[:, positions2]
                else:
                    new = recetario[comida][receta].copy().iloc[:, positions2]

                if day != last_day:
                    day_visitors2 = [sum(day_visitors[i:i + 6]) for i in range(0, len(day_visitors), 6)]
                    day_visitors2.insert(0, sum(day_visitors))
                    last_day = day
                    new_row = [f'Día {day}', '', day_visitors2[0]] + [''] + day_visitors2[1:] + ['']
                    cantidades.loc[len(cantidades)] = new_row

                new.iloc[:, 2:-2] = new.iloc[:, 2:-2] * day_visitors
                new2 = pd.concat([new.iloc[:, 0:2], new.iloc[:, 2:-2].sum(axis=1).round(5), new.iloc[:, -1]] +
                                 [new.iloc[:, 2 + i:2 + i + 6].sum(axis=1).round(5) for i in range(len(acampada))] + [new.iloc[:, -2]], axis=1)
                new2.columns = columns
                if comida in ['Desayuno', 'Almuerzo', 'Merienda', 'Pan_cena', 'Postre']:
                    cantidades = pd.concat([cantidades, new2, pd.DataFrame([[]])]).reset_index(drop=True)
                else:
                    cantidades = pd.concat([cantidades, new2]).reset_index(drop=True)

                cantidades = cantidades.fillna('').reset_index(drop=True)
        all_cantidades.append(cantidades)
    return all_cantidades


def get_asistentes_verano():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Asistentes!B3:AK19').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    asistentes = pd.DataFrame(x, columns=headers).fillna('').replace('', 0)
    asistentes.set_index('Dia', inplace=True)
    return asistentes


def get_asistentes_acampada():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Asistentes!B22:AK27').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    asistentes = pd.DataFrame(x, columns=headers).fillna('').replace('', 0)
    asistentes.set_index('Dia', inplace=True)
    return asistentes


def get_shopping_list_verano():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Cantidades!B2:Y').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')

    data['TOTAL'] = data['TOTAL'].replace('', 0.0).astype(float)
    indice = data[data['Recetas'] == 'Día 24'].index[0]
    primera_semana = data.loc[:indice - 1]
    segunda_semana = data.loc[indice:]

    primera_semana = primera_semana.loc[primera_semana.Ingredientes != '']
    primera_semana = primera_semana.iloc[:, 1:4]
    primera_semana = primera_semana.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()

    segunda_semana = segunda_semana.loc[segunda_semana.Ingredientes != '']
    segunda_semana = segunda_semana.iloc[:, 1:4]
    segunda_semana = segunda_semana.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()

    return primera_semana, segunda_semana


def get_shopping_list_acampada():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Cantidades2!B2:Y').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')

    columns_total = data.filter(like='TOTAL').columns
    data[columns_total] = data[columns_total].replace('', 0.0).astype(float)
    data = data.loc[:, ~data.columns.duplicated()].copy()
    data = data.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()
    data = data.drop_duplicates(subset=['Ingredientes', 'Medidas'])
    final_columns = ['Ingredientes', 'Medidas']
    final_columns.extend(columns_total)
    return data.loc[:, final_columns]


def get_shopping_list_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Cantidades_marcha!B2:X').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')
    data['TOTAL'] = data['TOTAL'].replace('', 0.0).astype(float)
    data = data.loc[data.Ingredientes != '']
    data = data.iloc[:, 1:4]
    data = data.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()
    return data


def get_inventario():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Inventario!B1:D').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')
    data['BASE'] = data['BASE'].astype(float)
    return data


def get_final_shopping_acampada():
    inventario = get_inventario()
    shopping_list = get_shopping_list_acampada()
    merged_df = pd.merge(inventario, shopping_list, on=['Ingredientes', 'Medidas'])
    # Merge para combinar los DataFrames en base a la columna 'Ingredientes'
    cols = ['Ingredientes', 'Medidas']
    merged_df = pd.merge(shopping_list, inventario, on=cols, how='left').fillna(0)
    campamentos = len(merged_df.columns) - 3

    for i in range(campamentos):
        # Restar los valores de 'Medidas' del inventario de los valores de 'TOTAL0'
        merged_df['Diferencia'] = merged_df[[f'BASE', f'TOTAL{i + 1}']].min(axis=1)
        merged_df[f'TOTAL{i + 1}'] = merged_df[f'TOTAL{i + 1}'] - merged_df['Diferencia']
        merged_df[f'BASE{i + 1}'] = merged_df[f'Diferencia']
        merged_df['BASE'] -= merged_df[f'BASE{i + 1}']
        cols.extend([f'TOTAL{i + 1}', f'BASE{i + 1}'])

    return merged_df.loc[1:, cols]


def update_shopping_list_campamento():
    first_week, second_week = get_shopping_list_verano()
    shopping_list_marcha = get_shopping_list_marcha()
    final_list = pd.concat([first_week, shopping_list_marcha]).groupby(['Ingredientes', 'Medidas'],
                                                                       as_index=False).sum()
    shoppping_day = get_all_shopping_day()
    data1 = [final_list.columns.values.tolist()]
    data1.extend(final_list.values.tolist())
    data2 = [second_week.columns.values.tolist()]
    data2.extend(second_week.values.tolist())
    data3 = [shoppping_day.columns.values.tolist()]
    data3.extend(shoppping_day.values.tolist())
    clear_sheet(ID_MENU, 'Lista_Compra')
    sheet = get_sheet(ID_MENU)
    append_data(sheet, 'Lista_Compra', 'B2', data1)
    append_data(sheet, 'Lista_Compra', 'H2', data2)
    append_data(sheet, 'Lista_Compra', 'L2', data3)


def update_shopping_list_acampada():
    final_list = get_final_shopping_acampada()
    data1 = [final_list.columns.values.tolist()]
    data1.extend(final_list.values.tolist())
    clear_sheet(ID_MENU, 'Lista_Compra')
    sheet = get_sheet(ID_MENU)
    append_data(sheet, 'Lista_Compra', 'B2', data1)


def update_cantidades_verano():
    servicio = get_servicio()
    menu = get_menu_verano()
    menu_marcha = get_menu_marcha()
    recetario = get_recetarios()
    asistentes = get_asistentes_verano()
    marcha = get_fechas_marcha()
    cantidades = get_cantidades_verano(menu, recetario, asistentes, marcha, servicio)
    cantidades_marcha = get_cantidades_marcha(menu_marcha, recetario, asistentes, marcha)
    data = [cantidades.columns.values.tolist()]
    data.extend(cantidades.values.tolist())
    clear_sheet(ID_MENU, 'Cantidades')
    sheet = get_sheet(ID_MENU)
    append_data(sheet, 'Cantidades', 'B2', data)
    data_marcha = [cantidades_marcha.columns.values.tolist()]
    data_marcha.extend(cantidades_marcha.values.tolist())
    clear_sheet(ID_MENU, 'Cantidades_marcha')
    append_data(sheet, 'Cantidades_marcha', 'B2', data_marcha)


def update_cantidades_acampada():
    menu = get_menu_acampada()
    recetario = get_recetarios()
    asistentes = get_asistentes_acampada()
    all_cantidades = get_cantidades_acampada(menu, recetario, asistentes)
    pos = 'B'
    clear_sheet(ID_MENU, 'Cantidades2')
    sheet = get_sheet(ID_MENU)
    for cantidades in all_cantidades:
        data = [cantidades.columns.values.tolist()]
        data.extend(cantidades.values.tolist())
        append_data(sheet, 'Cantidades2', f'{pos}2', data)
        pos = suma_columna(pos, len(data[0]) + 2)


def get_shopping_day():
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Cantidades!B2:E').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).fillna('')
    data['TOTAL'] = data['TOTAL'].replace('', 0.0).astype(float)
    select = {}
    for day in range(16, 31):
        if day == 16:
            index_start = 0
        else:
            index_day = data.index[data['Recetas'] == f'Día {day}'].tolist()[0]
            index_start = data.loc[index_day + 1:][data['Ingredientes'] == ''].index[0]
        if day == 30:
            index_end = data.index[-1]
        else:
            index_day = data.index[data['Recetas'] == f'Día {day + 1}'].tolist()[0]
            index_end = data.loc[index_day + 1:][data['Ingredientes'] == ''].index[0]
        temp = data.iloc[index_start:index_end, :]
        temp = temp[data['Ingredientes'].str.contains(r'\*', na=False)]
        temp.drop(['Recetas'], axis=1, inplace=True)
        temp = temp.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()

        select[f'Día {day}'] = temp
    return select


def get_shopping_day_marcha():
    fechas = get_fechas_marcha()
    x = spreadsheets.values().get(spreadsheetId=ID_MENU, range='Cantidades_marcha!B2:K').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).fillna('')
    cols = ['Castores', 'Manada', 'Tropa', 'Escultas', 'Rovers']
    data[cols] = data[cols].replace('', 0.0).astype(float)
    select = {}
    for unidad in range(0, 5):
        x = int(fechas[unidad][0]) - 1
        temp = pd.concat([data.iloc[:, 0:2], data.iloc[:, unidad + 4], data.iloc[:, 3]], axis=1)
        temp = temp[data['Ingredientes'].str.contains(r'\*', na=False)]
        temp.drop("Recetas", axis=1, inplace=True)
        temp = temp.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()
        temp.columns.values[2] = "TOTAL"
        if f'Día {x}' in select:
            temp = pd.concat([select[f'Día {x}'], temp], axis=0, ignore_index=True)
            temp = temp.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()

        select[f'Día {x}'] = temp

    return select


def get_all_shopping_day():
    select1 = get_shopping_day()
    select2 = get_shopping_day_marcha()

    for key in select1.keys():
        if key in select2:
            temp = pd.concat([select1[key], select2[key]], axis=0, ignore_index=True)
            temp = temp.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()
            select1[key] = temp

    dataframes = []

    for key, dataframe in select1.items():
        dataframes.append(pd.DataFrame([[key, '', '']], columns=dataframe.columns))

        dataframes.append(dataframe)

        dataframes.append(pd.DataFrame([['', '', '']], columns=dataframe.columns))

    data = pd.concat(dataframes, ignore_index=True)

    return data


async def update_all(update: Update, _: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    message = await chat.send_message(text=f'Generando cantidades y lista de la compra')
    message2 = await chat.send_sticker(sticker='CAACAgIAAxkBAAIJf2Perl8wSGXGavHr4598UvY10lLVAAIjAAMoD2oUJ1El54wgpAYuBA')
    update_cantidades_verano()
    update_shopping_list_acampada()
    await message.delete()
    await message2.delete()
    await chat.send_message(text=f'https://docs.google.com/spreadsheets/d/{ID_MENU}')


async def update_all_acampada(update: Update, _: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    message = await chat.send_message(text=f'Generando cantidades y lista de la compra')
    message2 = await chat.send_sticker(sticker='CAACAgIAAxkBAAIJf2Perl8wSGXGavHr4598UvY10lLVAAIjAAMoD2oUJ1El54wgpAYuBA')
    update_cantidades_acampada()
    update_shopping_list_acampada()
    await message.delete()
    await message2.delete()
    await chat.send_message(text=f'https://docs.google.com/spreadsheets/d/{ID_MENU}')


async def modificar_cantidades(_: Update, _2: ContextTypes.DEFAULT_TYPE):
    print()


async def menu_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    ut.set_actual_user(user.id, context)

    logger.warning(f"{user.first_name} entró en el comando menu")

    text = f"{user.first_name} ¿Qué quieres hacer?\n"

    keyboard = [[InlineKeyboardButton("🏡️Acampada🏡️", callback_data="ACAMPADA"),
                 InlineKeyboardButton("🏕️Verano🏕️", callback_data="VERANO")],
                [InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message(text, reply_markup=reply_markup)
    await update.message.delete()
    return MENU1


async def elegir_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data["type_menu"] = update.callback_query.data
    logger.warning(f"{user.first_name} eligió {update.callback_query.data}")

    text = f"{user.first_name} ¿Qué quieres hacer?\n"

    keyboard = [[InlineKeyboardButton("Generar cantidades", callback_data="GENERAR"),
                 InlineKeyboardButton("Modificar cantidades", callback_data="MODIFICAR")],
                [InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_chat.send_message(text, reply_markup=reply_markup)
    await update.callback_query.message.delete()
    return MENU2


async def terminar(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()

    return ConversationHandler.END


def get_conv_handler_menu():
    conv_handler_menu = ConversationHandler(
        entry_points=[CommandHandler('menu', menu_state)],
        states={
            MENU1: [
                CallbackQueryHandler(elegir_menu, pattern='.*'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR$')],
            MENU2: [
                CallbackQueryHandler(update_all_acampada, pattern='^GENERAR'),
                CallbackQueryHandler(modificar_cantidades, pattern='^MODIFICAR'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR$')
            ]
        },
        fallbacks=[CommandHandler('menu', menu_state)],
    )
    return conv_handler_menu



import cProfile

# prof = cProfile.Profile()
# prof.enable()
# update_cantidades_acampada()
# prof.disable()
# prof.print_stats(sort="tottime")
# get_shopping_list_acampada()
# if __name__ == "__main__":
#     get_all_shopping_day()
#     update_cantidades()
#     update_shopping_list()
