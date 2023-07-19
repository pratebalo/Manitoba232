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

lista_comidas = ['Desayuno', 'Almuerzo', 'Comida', 'Merienda', 'Cena', 'Pan', 'Postre']
columnas_excluir = ['Recetas', 'Ingredientes', 'Medidas']


def get_recetarios():
    recetario_global = {}
    for comida in lista_comidas:
        x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range=f'{comida}!B1:P1000').execute()['values']
        headers = x.pop(0)
        data = pd.DataFrame(x, columns=headers).dropna(how='all')
        columnas_restantes = [col for col in data.columns if col not in columnas_excluir]

        data[columnas_restantes] = data[columnas_restantes].replace('', 0.0).fillna(0.0).astype(float)
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
            temp = data.loc[pos:end]
            recetario[receta] = temp.iloc[:, 0:4]
            recetario[receta].insert(4, 'Jefes_castores', temp.Adultos)
            recetario[receta].insert(5, 'JefesC_vegan', temp.Adultos_vegan)
            recetario[receta].insert(6, 'Manada', temp.Manada)
            recetario[receta].insert(7, 'Manada_lact', temp.Manada_lact)
            recetario[receta].insert(8, 'Jefes_manada', temp.Adultos)
            recetario[receta].insert(9, 'JefesM_vegan', temp.Adultos_vegan)
            recetario[receta].insert(10, 'Tropa', temp.Tropa)
            recetario[receta].insert(11, 'Tropa_lact', temp.Tropa_lact)
            recetario[receta].insert(12, 'Jefes_tropa', temp.Adultos)
            recetario[receta].insert(13, 'JefesT_vegan', temp.Adultos_vegan)
            recetario[receta].insert(14, 'Escultas', temp.Adultos)
            recetario[receta].insert(15, 'Escultas_gluten', temp.Adultos_gluten)
            recetario[receta].insert(16, 'Jefes_escultas', temp.Adultos)
            recetario[receta].insert(17, 'JefesE_vegan', temp.Adultos_vegan)
            recetario[receta].insert(18, 'JefesE_vegan_lact', temp.Adultos_vegan_lact)
            recetario[receta].insert(19, 'Rovers', temp.Adultos)
            recetario[receta].insert(20, 'Rovers_lact', temp.Adultos_lact)
            recetario[receta].insert(21, 'Jefes_rovers', temp.Adultos)
            recetario[receta].insert(22, 'JefesR_vegan', temp.Adultos_vegan)
            recetario[receta].insert(23, 'Intendentes', temp.Adultos)
            recetario[receta].insert(24, 'Comun', temp.Comun)
            recetario[receta].insert(25, 'Medidas', temp.Medidas)

        recetario_global[comida] = recetario

    return recetario_global


def get_menu_acampada():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_verano!A3:11').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_menu_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_verano!A14:D19').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (len(headers) - len(item)))
    menu = pd.DataFrame(x, columns=headers).fillna('')
    menu.set_index('Comida', inplace=True)
    return menu


def get_fechas_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_verano!G15:H19').execute()['values']
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
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_verano!K15:M17').execute()['values']
    lista_resultante = [[x[0][0], str(int(x[0][0]) + 1)], [x[1][0], str(int(x[1][0]) + 1), int(x[1][1])],
                        [x[2][0], str(int(x[2][0]) + 1), str(int(x[2][0]) + 2), x[2][2]]]

    return lista_resultante


def get_cantidades(menu, recetario, asistentes, marcha, servicio):
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


def get_asistentes():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Asistentes_verano!B3:X19').execute()['values']
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


def get_shopping_list_marcha():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Cantidades_marcha!B2:X').execute()['values']
    headers = x.pop(0)
    data = pd.DataFrame(x, columns=headers).dropna(how='all')
    data['TOTAL'] = data['TOTAL'].replace('', 0.0).astype(float)
    data = data.loc[data.Ingredientes != '']
    data = data.iloc[:, 1:4]
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
    servicio = get_servicio()
    menu = get_menu_acampada()
    menu_marcha = get_menu_marcha()
    recetario = get_recetarios()
    asistentes = get_asistentes()
    marcha = get_fechas_marcha()
    cantidades = get_cantidades(menu, recetario, asistentes, marcha, servicio)
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
