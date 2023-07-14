from utils.sheets_drive import spreadsheets, get_sheet, append_data, clear_sheet
import warnings
import logging
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import (CommandHandler, PollAnswerHandler, CallbackQueryHandler, ConversationHandler, CallbackContext,
                          MessageHandler, Filters, Updater
                          )

MENU1, MENU2, CREAR_LISTA2, EDITAR_LISTA1, EDITAR_LISTA2, EDITAR_LISTA_A, EDITAR_LISTA_E, ELIMINAR_LISTA, \
    FINAL_OPTION = range(9)
warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("menu")
logging.getLogger('apscheduler').propagate = False
ID_ACAMPADA = '1rzVO8jNACvcynnaaAJd83nFpsEk7hbnL9XSXNFEpPO4'
ID_VERANO = ''
sheet = get_sheet(ID_ACAMPADA)

lista_comidas = ['Desayuno', 'Almuerzo', 'Comida', 'Merienda', 'Cena']


def get_recetarios():
    recetario_global = {}
    for comida in lista_comidas:
        x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range=f'{comida}!B1:P1000').execute()['values']
        headers = x.pop(0)
        data = pd.DataFrame(x, columns=headers).dropna(how='all')
        data[['Castores', 'Castores_lact', 'Manada', 'Tropa', 'Escultas', 'Escultas_gluten', 'Rovers', 'Rovers_lact',
              'Jefes', 'Jefes_vegan', 'Jefes_vegan_lact', 'Comun']] = data[
            ['Castores', 'Castores_lact', 'Manada', 'Tropa', 'Escultas', 'Escultas_gluten', 'Rovers', 'Rovers_lact',
             'Jefes', 'Jefes_vegan', 'Jefes_vegan_lact', 'Comun']].replace('',
                                                                           0.0).astype(
            float)
        merges = spreadsheets.get(spreadsheetId=ID_ACAMPADA, ranges=f'{comida}!B1:K1000').execute()['sheets'][0]
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
            recetario[receta].insert(4, 'Jefes_castores', recetario[receta].Jefes)
            recetario[receta].insert(6, 'Jefes_manada', recetario[receta].Jefes)
            recetario[receta].insert(8, 'Jefes_tropa', recetario[receta].Jefes)
            recetario[receta].insert(11, 'Jefes_escultas', recetario[receta].Jefes)
            recetario[receta].insert(5, 'JefesC_vegan', recetario[receta].Jefes_vegan)
            recetario[receta].insert(8, 'JefesM_vegan', recetario[receta].Jefes_vegan)
            recetario[receta].insert(11, 'JefesT_vegan', recetario[receta].Jefes_vegan)
            recetario[receta].insert(15, 'JefesE_vegan', recetario[receta].Jefes_vegan)
            recetario[receta].insert(16, 'JefesE_vegan_lact', recetario[receta].Jefes_vegan_lact)
            recetario[receta].insert(21, 'Intendentes', recetario[receta].Jefes)
            recetario[receta] = recetario[receta].rename(columns={'Jefes_vegan': 'JefesR_vegan'})
            recetario[receta] = recetario[receta].rename(columns={'Jefes': 'Jefes_rover'})
            recetario[receta].drop("Jefes_vegan_lact", axis=1, inplace=True)

        recetario_global[comida] = recetario

    return recetario_global


def get_menu_acampada():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_acampada!C3:S8').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_menu_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_verano!N3:Q8').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_fechas_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_verano!T4:U8').execute()['values']
    lista_resultante = []

    for sublista in x:
        if int(sublista[1]) - int(sublista[0]) == 1:
            sublista.insert(1, '0')
            lista_intermedia = sublista
        else:
            lista_intermedia = [str(i) for i in range(int(sublista[0]), int(sublista[1]) + 1)]
        lista_resultante.append(lista_intermedia)
    return lista_resultante


def get_cantidades(menu, recetario, asistentes, marcha):
    cantidades = pd.DataFrame(
        columns=['Recetas', 'Ingredientes', 'Castores', 'Castores_lact', 'Jefes_castores', 'JefesC_vegan', 'Manada',
                 'Jefes_manada', 'JefesM_vegan', 'Tropa', 'Jefes_tropa', 'JefesT_vegan', 'Escultas', 'Escultas_gluten',
                 'Jefes_escultas', 'JefesE_vegan', 'JefesE_vegan_lact', 'Rovers', 'Rovers_lact', 'Jefes_rover',
                 'JefesR_vegan', 'Intendentes', 'Comun', 'Medidas'])
    day = None
    for col in menu:
        for ix in menu.index:
            if not menu.at[ix, col]:
                continue

            day_visitors = list(map(int, asistentes.loc[[col]].values.tolist()[0]))
            if col != day:
                day = col
                new_row = [f'Día {col}', ''] + day_visitors + ['', '']
                cantidades.loc[len(cantidades)] = new_row

            receta = menu.at[ix, col]
            new = recetario[ix][receta].copy()
            new.iloc[:, 2:22] = new.iloc[:, 2:22] * day_visitors
            cantidades = pd.concat([cantidades, new, pd.DataFrame([[]])]).reset_index(drop=True)

    cantidades = cantidades.fillna('').reset_index(drop=True)
    return cantidades


def get_cantidades_marcha(menu, recetario, asistentes, fechas):
    asistentes.drop(['Intendentes'], axis=1, inplace=True)
    cantidades = pd.DataFrame(
        columns=['Recetas', 'Ingredientes', 'Castores', 'Castores_lact', 'Jefes_castores', 'JefesC_vegan', 'Manada',
                 'Jefes_manada', 'JefesM_vegan', 'Tropa', 'Jefes_tropa', 'JefesT_vegan', 'Escultas', 'Escultas_gluten',
                 'Jefes_escultas', 'JefesE_vegan', 'JefesE_vegan_lact', 'Rovers', 'Rovers_lact', 'Jefes_rover',
                 'JefesR_vegan', 'Comun', 'Medidas'])
    lista = {0: [0, 4],
             1: [4, 7],
             2: [7, 10],
             3: [10, 15],
             4: [15, 19]
             }
    day = None
    for col in menu:
        for ix in menu.index:
            if not menu.at[ix, col]:
                continue
            day_visitors = []
            for i in range(0, 5):
                if fechas[i][int(col) - 1] == '0':
                    day_visitors.extend([0, 0, 0, 0])
                else:
                    select = asistentes.loc[fechas[i][int(col) - 1]].tolist()[lista[i][0]:lista[i][1]]
                    day_visitors.extend(list(map(int, select)))
            if col != day:
                day = col
                new_row = [f'Día {col}', ''] + day_visitors + ['', '']
                cantidades.loc[len(cantidades)] = new_row

            receta = menu.at[ix, col]
            new = recetario[ix][receta].copy().drop(['Intendentes'], axis=1)
            new.iloc[:, 2:21] = new.iloc[:, 2:21] * day_visitors
            cantidades = pd.concat([cantidades, new, pd.DataFrame([[]])]).reset_index(drop=True)

    cantidades = cantidades.fillna('').reset_index(drop=True)
    return cantidades


def get_asistentes():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Asistentes_verano!B3:V19').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    asistentes = pd.DataFrame(x, columns=headers).fillna('')
    asistentes.set_index('Dia', inplace=True)
    return asistentes


def get_shopping_list():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Cantidades!B2:Y').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')
    cols = ['Castores', 'Castores_lact', 'Jefes_castores', 'JefesC_vegan', 'Manada', 'Jefes_manada', 'JefesM_vegan',
            'Tropa',
            'Jefes_tropa', 'JefesT_vegan', 'Escultas', 'Escultas_gluten', 'Jefes_escultas', 'JefesE_vegan',
            'JefesE_vegan_lact', 'Rovers', 'Rovers_lact', 'Jefes_rover',
            'JefesR_vegan', 'Intendentes', 'Comun']

    data[cols] = data[cols].replace('', 0.0).astype(float)
    indice = data[data['Recetas'] == 'Día 24'].index[0]
    primera_semana = data.loc[:indice - 1]
    segunda_semana = data.loc[indice:]

    primera_semana = primera_semana.loc[primera_semana.Ingredientes != '']
    primera_semana.drop('Recetas',axis=1,inplace=True)
    primera_semana['Total'] = primera_semana.iloc[:, 1:22].sum(axis=1)
    primera_semana = primera_semana.drop(cols, axis=1)
    primera_semana = primera_semana.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()

    segunda_semana = segunda_semana.loc[segunda_semana.Ingredientes != '']
    segunda_semana.drop('Recetas',axis=1,inplace=True)
    segunda_semana['Total'] = segunda_semana.iloc[:, 1:22].sum(axis=1)
    segunda_semana = segunda_semana.drop(cols, axis=1)
    segunda_semana = segunda_semana.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()

    return primera_semana, segunda_semana


def get_shopping_list_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Cantidades_marcha!C2:X').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')
    cols = ['Castores', 'Castores_lact', 'Jefes_castores', 'JefesC_vegan', 'Manada', 'Jefes_manada', 'JefesM_vegan',
            'Tropa', 'Jefes_tropa', 'JefesT_vegan', 'Escultas', 'Escultas_gluten', 'Jefes_escultas', 'JefesE_vegan',
            'JefesE_vegan_lact', 'Rovers', 'Rovers_lact', 'Jefes_rover', 'JefesR_vegan', 'Comun']
    data[cols] = data[cols].replace('', 0.0).astype(float)
    data = data.loc[data.Ingredientes != '']
    data['Total'] = data.iloc[:, 1:21].sum(axis=1)
    data = data.drop(cols, axis=1)
    data = data.groupby(['Ingredientes', 'Medidas'], as_index=False).sum()
    return data


def update_shopping_list():
    first_week, second_week = get_shopping_list()
    shopping_list_marcha = get_shopping_list_marcha()
    final_list = pd.concat([first_week, shopping_list_marcha]).groupby(['Ingredientes', 'Medidas'],
                                                                          as_index=False).sum()
    data1 = [final_list.columns.values.tolist()]
    data1.extend(final_list.values.tolist())
    data2 = [second_week.columns.values.tolist()]
    data2.extend(second_week.values.tolist())
    clear_sheet(ID_ACAMPADA, 'Lista_Compra')
    append_data(sheet, 'Lista_Compra', 'B2', data1)
    append_data(sheet, 'Lista_Compra', 'H2', data2)


def update_cantidades():
    menu = get_menu_acampada()
    menu_marcha = get_menu_marcha()
    recetario = get_recetarios()
    asistentes = get_asistentes()
    marcha = get_fechas_marcha()
    cantidades = get_cantidades(menu, recetario, asistentes, marcha)
    cantidades_marcha = get_cantidades_marcha(menu_marcha, recetario, asistentes, marcha)
    data = [cantidades.columns.values.tolist()]
    data.extend(cantidades.values.tolist())
    clear_sheet(ID_ACAMPADA, 'Cantidades')
    append_data(sheet, 'Cantidades', 'B2', data)
    data_marcha = [cantidades_marcha.columns.values.tolist()]
    data_marcha.extend(cantidades_marcha.values.tolist())
    clear_sheet(ID_ACAMPADA, 'Cantidades_marcha')
    append_data(sheet, 'Cantidades_marcha', 'B2', data_marcha)


def update_all(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    message = context.bot.sendMessage(chat_id, text=f'Generando cantidades y lista de la compra')
    'CAACAgIAAxkBAAIJf2Perl8wSGXGavHr4598UvY10lLVAAIjAAMoD2oUJ1El54wgpAYuBA'
    message2 = context.bot.sendSticker(chat_id=chat_id,
                                       sticker='CAACAgIAAxkBAAIJf2Perl8wSGXGavHr4598UvY10lLVAAIjAAMoD2oUJ1El54wgpAYuBA')
    update_cantidades()
    update_shopping_list()
    context.bot.deleteMessage(chat_id=chat_id, message_id=message.message_id)
    context.bot.deleteMessage(chat_id=chat_id, message_id=message2.message_id)
    context.bot.sendMessage(chat_id, text=f'https://docs.google.com/spreadsheets/d/{ID_ACAMPADA}')


def modificar_cantidades(update: Update, context: CallbackContext):
    print()


def menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user = update.effective_user
    id_mensaje = update.message.message_id

    logger.warning(f"{update.effective_chat.type} -> {user.first_name} entró en el comando menu")

    text = f"{user.first_name} ¿Qué quieres hacer?\n"

    keyboard = [[InlineKeyboardButton("🏡️Acampada🏡️", callback_data="ACAMPADA"),
                 InlineKeyboardButton("🏕️Verano🏕️", callback_data="VERANO")],
                [InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    context.bot.deleteMessage(chat_id, id_mensaje)
    return MENU1


def elegir_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user = update.effective_user
    id_mensaje = update.callback_query.message.message_id
    context.user_data["type_menu"] = update.callback_query.data
    logger.warning(f"{update.effective_chat.type} -> {user.first_name} eligió {update.callback_query.data}")

    text = f"{user.first_name} ¿Qué quieres hacer?\n"

    keyboard = [[InlineKeyboardButton("Generar cantidades", callback_data="GENERAR"),
                 InlineKeyboardButton("Modificar cantidades", callback_data="MODIFICAR")],
                [InlineKeyboardButton("Terminar", callback_data=str("TERMINAR"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.sendMessage(chat_id, text, reply_markup=reply_markup)
    context.bot.deleteMessage(chat_id, id_mensaje)
    return MENU2


def terminar(update: Update, context: CallbackContext):
    update.callback_query.delete_message()

    return ConversationHandler.END


def get_conv_handler_menu():
    conv_handler_menu = ConversationHandler(
        entry_points=[CommandHandler('menu', menu)],
        states={
            MENU1: [
                CallbackQueryHandler(elegir_menu, pattern='.*'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR$')],
            MENU2: [
                CallbackQueryHandler(update_all, pattern='^GENERAR'),
                CallbackQueryHandler(modificar_cantidades, pattern='^MODIFICAR'),
                CallbackQueryHandler(terminar, pattern='^TERMINAR$')
            ]
        },
        fallbacks=[CommandHandler('menu', menu)],
    )
    return conv_handler_menu


if __name__ == "__main__":
    update_cantidades()
    update_shopping_list()
