from utils.sheets_drive import spreadsheets, get_sheet, append_data, clear_sheet
import pandas as pd
from telegram import Update
from telegram.ext import CallbackContext

sheet_id = '1rzVO8jNACvcynnaaAJd83nFpsEk7hbnL9XSXNFEpPO4'
sheet = get_sheet(sheet_id)

lista_comidas = ['Desayuno', 'Almuerzo', 'Comida', 'Merienda', 'Cena']


def get_recetarios():
    recetario_global = {}
    for comida in lista_comidas:
        x = spreadsheets.values().get(spreadsheetId=sheet_id, range=f'{comida}!B1:K1000').execute()['values']
        headers = x.pop(0)
        data = pd.DataFrame(x, columns=headers).dropna(how='all')
        data[['Castores', 'Manada', 'Tropa', 'Escultas', 'Rovers', 'Jefes', 'Comun']] = data[
            ['Castores', 'Manada', 'Tropa', 'Escultas', 'Rovers', 'Jefes', 'Comun']].replace('', 0.0).astype(float)
        merges = spreadsheets.get(spreadsheetId=sheet_id, ranges=f'{comida}!B1:K1000').execute()['sheets'][0]
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
            recetario[receta] = data.loc[pos:end]
            recetario[receta].insert(3, 'Jefes_castores', recetario[receta].Jefes)
            recetario[receta].insert(5, 'Jefes_manada', recetario[receta].Jefes)
            recetario[receta].insert(7, 'Jefes_tropa', recetario[receta].Jefes)
            recetario[receta].insert(9, 'Jefes_escultas', recetario[receta].Jefes)
            recetario[receta] = recetario[receta].rename(columns={'Jefes': 'Jefes_rover'})

        recetario_global[comida] = recetario

    return recetario_global


def get_menu_acampada():
    x = spreadsheets.values().get(spreadsheetId=sheet_id, range='Menú_acampada!C3:H8').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (6 - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_cantidades(menu, recetario, asistentes):
    cantidades = pd.DataFrame(
        columns=['Recetas', 'Ingredientes', 'Castores', 'Jefes_castores', 'Manada', 'Jefes_manada', 'Tropa',
                 'Jefes_tropa', 'Escultas', 'Jefes_escultas', 'Rovers', 'Jefes_rover', 'Comun', 'Medidas'])
    day = None
    for col in menu:
        for ix in menu.index:
            if not menu.at[ix, col]:
                break

            if col != day:
                day = col
                day_visitors = list(map(int, asistentes.loc[[col]].values.tolist()[0]))
                new_row = [f'Día {col}', ''] + day_visitors + ['', '']
                cantidades.loc[len(cantidades)] = new_row

            receta = menu.at[ix, col]
            new = recetario[ix][receta].copy()
            new.iloc[:, 2:12] = new.iloc[:, 2:12] * day_visitors
            cantidades = pd.concat([cantidades, new, pd.DataFrame([[]])])

    cantidades = cantidades.fillna('').reset_index(drop=True)
    return cantidades


def get_asistentes():
    x = spreadsheets.values().get(spreadsheetId=sheet_id, range='Asistentes!B3:L8').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (6 - len(item)))
    asistentes = pd.DataFrame(x, columns=headers).fillna('')
    asistentes.set_index('Dia', inplace=True)
    return asistentes


def get_shopping_list():
    x = spreadsheets.values().get(spreadsheetId=sheet_id, range='Cantidades!C2:O').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')
    cols = ['Castores', 'Jefes_castores', 'Manada', 'Jefes_manada', 'Tropa', 'Jefes_tropa', 'Escultas',
            'Jefes_escultas', 'Rovers', 'Jefes_rover', 'Comun']
    data[cols] = data[cols].replace('', 0.0).astype(float)
    data = data.loc[data.Ingredientes != '']
    data['Total'] = data.iloc[:, 1:11].sum(axis=1)
    data = data.drop(cols, axis=1)
    data = data.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()
    return data


def update_shopping_list():
    shopping_list = get_shopping_list()
    data = [shopping_list.columns.values.tolist()]
    data.extend(shopping_list.values.tolist())
    clear_sheet(sheet_id, 'Lista_Compra')
    append_data(sheet, 'Lista_Compra', 'B2', data)


def update_cantidades():
    menu = get_menu_acampada()
    recetario = get_recetarios()
    asistentes = get_asistentes()
    cantidades = get_cantidades(menu, recetario, asistentes)
    data = [cantidades.columns.values.tolist()]
    data.extend(cantidades.values.tolist())
    clear_sheet(sheet_id, 'Cantidades')
    append_data(sheet, 'Cantidades', 'B2', data)


def update_all(update: Update, context: CallbackContext):
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    chat_id = update.effective_chat.id
    update_cantidades()
    update_shopping_list()
    context.bot.sendMessage(chat_id, text=f'https://docs.google.com/spreadsheets/d/{sheet_id}')
