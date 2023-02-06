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
        x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range=f'{comida}!B1:K1000').execute()['values']
        headers = x.pop(0)
        data = pd.DataFrame(x, columns=headers).dropna(how='all')
        data[['Castores', 'Manada', 'Tropa', 'Escultas', 'Rovers', 'Jefes', 'Comun']] = data[
            ['Castores', 'Manada', 'Tropa', 'Escultas', 'Rovers', 'Jefes', 'Comun']].replace('', 0.0).astype(float)
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
            recetario[receta].insert(3, 'Jefes_castores', recetario[receta].Jefes)
            recetario[receta].insert(5, 'Jefes_manada', recetario[receta].Jefes)
            recetario[receta].insert(7, 'Jefes_tropa', recetario[receta].Jefes)
            recetario[receta].insert(9, 'Jefes_escultas', recetario[receta].Jefes)
            recetario[receta] = recetario[receta].rename(columns={'Jefes': 'Jefes_rover'})

        recetario_global[comida] = recetario

    return recetario_global


def get_menu_acampada():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Menú_acampada!C3:H8').execute()['values']
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
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Asistentes!B3:L8').execute()['values']
    headers = x.pop(0)
    for item in x:
        item.extend([''] * (6 - len(item)))
    asistentes = pd.DataFrame(x, columns=headers).fillna('')
    asistentes.set_index('Dia', inplace=True)
    return asistentes


def get_shopping_list():
    x = spreadsheets.values().get(spreadsheetId=ID_ACAMPADA, range='Cantidades!C2:O').execute()['values']
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
    clear_sheet(ID_ACAMPADA, 'Lista_Compra')
    append_data(sheet, 'Lista_Compra', 'B2', data)


def update_cantidades():
    menu = get_menu_acampada()
    recetario = get_recetarios()
    asistentes = get_asistentes()
    cantidades = get_cantidades(menu, recetario, asistentes)
    data = [cantidades.columns.values.tolist()]
    data.extend(cantidades.values.tolist())
    clear_sheet(ID_ACAMPADA, 'Cantidades')
    append_data(sheet, 'Cantidades', 'B2', data)


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
