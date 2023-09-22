from utils import logger_config 
import re
import requests
import os
import pandas as pd
import src.utilitys as ut
from datetime import datetime
from utils.sheets_drive import get_sheet, append_data, clear_sheet
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, CallbackContext, MessageHandler, Filters

from utils import database as db
from utils import client_drive
from decouple import config

# Stages
OPTION, POT, POT2, POT3, PAY, PAY2, FINAL_OPTION, IBAN, IBAN2, EXPENSES, DELETE_EXPENSE, EDIT_EXPENSE, EDIT_CONCEPT, EDIT_PRICE, EDIT_TICKET, EDIT_CONCEPT2, \
    EDIT_PRICE2, EDIT_TICKET2 = range(18)
ID_MANITOBA = int(config("ID_MANITOBA"))
ID_TESORERIA = int(config("ID_TESORERIA"))
ID_ADMIN = int(config("ID_ADMIN"))
ID_SHEET_EXPENSES = config("ID_SHEET_EXPENSES")
logger = logger_config.logger


def treasury(update: Update, context: CallbackContext):
    ut.set_actual_user(update.effective_user.id, context)
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} entro en el comando asistencia")
    if update.message:
        update.message.delete()
    else:
        update.callback_query.delete_message()
    text = f"<b>Tesoreria</b>\n¿Qué quieres hacer?\n"
    keyboard = [
        # [InlineKeyboardButton("Meter dinero en el bote", callback_data="+")],
        # [InlineKeyboardButton("Sacar dinero del bote", callback_data="-")],
        [InlineKeyboardButton("Comunicar un gasto", callback_data="EXPENSE")],
        [InlineKeyboardButton("Cambiar mi número de cuenta", callback_data="ACCOUNT")],
        [InlineKeyboardButton("Mis gastos", callback_data="MINE")]]
    if update.effective_user.id == ID_TESORERIA or update.effective_user.id == ID_ADMIN:
        keyboard.append([InlineKeyboardButton("A PAGAR A PAGAR 🤑🤑", callback_data="PAY")])
    keyboard.append([InlineKeyboardButton("Terminar", callback_data="END")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.sendMessage(update.effective_chat.id, text, parse_mode="HTML", reply_markup=reply_markup)
    return OPTION


def expenses_state(update: Update, context: CallbackContext):
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} accedio al apartado gastos")

    all_expenses = db.select("expenses").sort_values(by=["paid", "id"], ascending=True, ignore_index=True)
    context.user_data["all_expenses"] = all_expenses
    my_expenses = all_expenses[all_expenses.id_person == update.effective_user.id].reset_index()

    text = "No tienes gastos sin pagar" if my_expenses.empty else "Estos son tus gastos:"
    keyboard = []
    for i, expense in my_expenses.iterrows():
        price = "{:.2f}".format(expense.price)
        text += f"\n{i + 1}. {'✅' if expense.paid else '❌'}{price}€ - {expense.date.strftime('%d/%m/%Y')} - {expense.concept}"
        keyboard.append([InlineKeyboardButton(i + 1, callback_data=f"N"),
                         InlineKeyboardButton("✍️", callback_data=f"EDIT{expense.id}"),
                         InlineKeyboardButton("🗑️", callback_data=f"DELETE{expense.id}")])

    keyboard.append([InlineKeyboardButton("Atras", callback_data=str("BACK")),
                     InlineKeyboardButton("Terminar", callback_data=str("END"))])
    if update.callback_query.message.photo or update.callback_query.message.document:
        update.callback_query.delete_message()
        context.bot.sendMessage(update.effective_chat.id, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return EXPENSES


def delete_expense(update: Update, context: CallbackContext):
    id_expense = int(update.callback_query.data.replace("DELETE", ""))
    all_expenses = context.user_data["all_expenses"]

    expense = all_expenses[all_expenses.id == id_expense].squeeze()
    if expense.paid:
        context.bot.sendMessage(update.effective_chat.id, f"El gasto no se puede eliminar porque ya ha sido pagado")
    else:
        text = f"¿Seguro que quieres eliminar el gasto?"
        keyboard = [[InlineKeyboardButton("Eliminar", callback_data="DELETE" + str(id_expense)),
                     InlineKeyboardButton("Volver atrás", callback_data="BACK")]]

        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return DELETE_EXPENSE


def delete_expense2(update: Update, context: CallbackContext):
    id_expense = int(update.callback_query.data.replace("DELETE", ""))
    expense = db.delete("expenses", id_expense).iloc[0]
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha eliminado el gasto '{expense.to_list()}'")
    client_drive.delete_file(expense.id_file)
    expenses_state(update, context)
    update_drive_expenses()
    return EXPENSES


def edit_expense(update: Update, context: CallbackContext):
    if update.callback_query:
        context.user_data["id_expense"] = int(update.callback_query.data.replace("EDIT", ""))

    all_expenses = db.select("expenses").sort_values(by=["paid", "id"], ascending=True, ignore_index=True)
    expense = all_expenses[all_expenses.id == context.user_data["id_expense"]].squeeze()
    context.user_data["expense"] = expense
    if expense.paid:
        context.bot.sendMessage(update.effective_chat.id, f"El gasto no se puede editar porque ya ha sido pagado")
    else:
        if update.callback_query:
            update.callback_query.delete_message()
        text = f"Seleccione el campo que quiera editar"
        keyboard = [[InlineKeyboardButton(f"{expense.price}€", callback_data=f"PRICE")],
                    [InlineKeyboardButton(expense.concept, callback_data=f"CONCEPT")],
                    [InlineKeyboardButton("📷Ticket/Factura📷", callback_data=f"TICKET")],
                    [InlineKeyboardButton("CANCELAR", callback_data=f"BACK")]]
        filename, file = client_drive.get_file_by_id(expense.id_file)
        if expense.photo:
            context.bot.sendPhoto(chat_id=update.effective_chat.id, photo=file, caption=text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            context.bot.sendDocument(chat_id=update.effective_chat.id, document=file, filename=filename, caption=text,
                                     reply_markup=InlineKeyboardMarkup(keyboard))

        return EDIT_EXPENSE


def edit_price(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, "Introduce el nuevo precio del gasto")

    return EDIT_PRICE


def edit_price2(update: Update, context: CallbackContext):
    new_price = re.sub('[^\\d.]', '', update.message.text.replace(",", "."))
    update.message.delete()
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    try:
        new_price = float(new_price)
        db.update_field_table(idx=context.user_data["expense"].id, table="expenses", values=[new_price], fields=["price"])

        edit_expense(update, context)
        update_drive_expenses()
        return EDIT_EXPENSE

    except ValueError:
        context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id,
                                                                  f"La cantidad introducida no es valida, pruebe de nuevo")
        return EDIT_PRICE


def edit_concept(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, "Introduce el numero concepto del gasto")
    return EDIT_CONCEPT


def edit_concept2(update: Update, context: CallbackContext):
    new_concept = update.message.text
    update.message.delete()
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)

    db.update_field_table(idx=context.user_data["expense"].id, table="expenses", values=[new_concept], fields=["concept"])

    edit_expense(update, context)
    update_drive_expenses()
    return EDIT_EXPENSE


def edit_ticket(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, "Enviame la foto o archivo con el nuevo ticket")
    return EDIT_TICKET


def edit_ticket2(update: Update, context: CallbackContext):
    data = db.select("data")
    if update.message.photo:
        data_ticket, ext_ticket = download_file_telegram(context, update.message.photo[-1])
    else:
        data_ticket, ext_ticket = download_file_telegram(context, update.message.document)
    id_expense = context.user_data['expense'].id
    persona = data[data.id == update.effective_user.id].squeeze()
    file_name = f"{id_expense}_{persona.nombre} {persona.apellidos}{ext_ticket}"
    update.message.delete()
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    id_file = client_drive.upload_file(data=data_ticket, file_name=file_name, parent_id=client_drive.FOLDER_EXPENSES)
    db.update_expense_file(id_expense, id_file)
    client_drive.delete_file(context.user_data['expense'].id_file)

    edit_expense(update, context)
    update_drive_expenses()
    return EDIT_EXPENSE


def bote_state(update: Update, context: CallbackContext):
    context.user_data["expense_type"] = update.callback_query.data

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = update.callback_query.edit_message_text(f"¿Cuánto dinero ha sido?", reply_markup=keyboard)

    return POT


def bote2(update: Update, context: CallbackContext):
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha enviado la cantidad {update.message.text}")
    context.user_data["price"] = re.sub('[^\\d.]', '', update.message.text.replace(",", "."))
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    try:
        float(context.user_data["price"])
        context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, f"¿Cúal es el motivo del gasto?", reply_markup=keyboard)
        return POT2

    except ValueError:
        context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, f"La cantidad introducida no es valida, pruebe de nuevo",
                                                                  reply_markup=keyboard)

        return POT


def bote3(update: Update, context: CallbackContext):
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha enviado el motivo {update.message.text}")

    context.user_data["motivo"] = update.message.text
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = context.bot.sendMessage(
        update.effective_chat.id, f" Necesito que me envies una foto o documento del ticket, si no tienes pues enviame un selfie haciendo el idiota",
        reply_markup=keyboard)

    return POT3


def bote4(update: Update, context: CallbackContext):
    data = db.select("data")
    bote = db.select("botes")
    motivo = context.user_data["motivo"]
    persona = data[data.id == update.effective_user.id].squeeze()
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha enviado una foto")
    if context.user_data["expense_type"] == "EXPENSE":
        cantidad = float(context.user_data["price"])
        if update.message.photo:
            photo = True
            data_ticket, ext_ticket = download_file_telegram(context, update.message.photo[-1].file_id)
        else:
            photo = False
            data_ticket, ext_ticket = download_file_telegram(context, update.message.document.file_id)
        inserted_expense = db.insert_expense(persona.id,
                                             motivo,
                                             cantidad,
                                             datetime.today().strftime('%d/%m/%Y'),
                                             photo)
        expense_id = inserted_expense.id
        file_name = f"{expense_id}_{persona.nombre} {persona.apellidos}{ext_ticket}"

        id_file = client_drive.upload_file(data=data_ticket, file_name=file_name, parent_id=client_drive.FOLDER_EXPENSES)
        db.update_expense_file(expense_id, id_file)
        treasurer_message = f"{persona.apodo} ha gastado {cantidad}€ en '{motivo}'"
        user_message = f"Has metido el gasto de {cantidad}€ con el concepto '{motivo}'"
        filename, file = client_drive.get_file_by_id(id_file)
        if photo:
            context.bot.sendPhoto(chat_id=ID_TESORERIA, photo=file, caption=treasurer_message)
        else:
            context.bot.sendDocument(chat_id=ID_TESORERIA, document=file, filename=filename, caption=treasurer_message)
    else:
        cantidad = float(context.user_data["expense_type"] + context.user_data["price"])
        bote_actual = bote.iloc[-1].total + cantidad
        db.insert_bote(update.effective_user.id,
                       cantidad,
                       bote_actual,
                       update.message.text)
        if context.user_data["expense_type"] == "+":
            treasurer_message = f"{persona.apodo} ha metido {context.user_data['price']}€ " \
                                f"en el bote con el concepto '{motivo}'.\nHay {bote_actual}€ en el bote"
        else:
            treasurer_message = f"{persona.apodo} ha sacado {context.user_data['price']}€ " \
                                f"del bote con el concepto '{motivo}'.\nHay {bote_actual}€ en el bote"
        user_message = f"Bote actualizado.\nHay {bote_actual}€ en el bote"
        context.bot.sendMessage(ID_TESORERIA, treasurer_message)

    context.bot.sendMessage(update.effective_chat.id, user_message)
    update_drive_expenses()
    return ConversationHandler.END


def download_file_telegram(context, file_id):
    file = context.bot.get_file(file_id)

    response = requests.get(file.file_path)
    if response.status_code == 200:
        return response.content, os.path.splitext(file.file_path)[1]

    else:
        logger.warning("Error al descargar la imagen")


def pay(update: Update, _: CallbackContext):
    expenses = db.select("expenses").sort_values(by=["paid", "id_person"], ignore_index=True)
    data = db.select("data")
    keyboard = []
    texto = f"A soltar el dinero 💰💶💵💷💸\n"
    expenses_grouped = expenses[~expenses.paid].groupby('id_person')['price'].sum().reset_index()
    for expense in expenses_grouped.itertuples():
        keyboardline = []
        name = data[data.id == expense.id_person].squeeze().apodo
        # texto += f" {i + 1}. ({expense.date.strftime('%d/%m')}) {expense.price}€ -> {expense.concept}\n"
        keyboardline.append(InlineKeyboardButton(name, callback_data="NOTHING"))
        keyboardline.append(InlineKeyboardButton(f"{expense.price}€", callback_data="NOTHING"))
        keyboardline.append(InlineKeyboardButton("💰", callback_data="PAY" + str(expense.id_person)))
        keyboard.append(keyboardline)

    keyboard.extend([[InlineKeyboardButton("Atrás", callback_data="BACK"), InlineKeyboardButton("Terminar", callback_data="END")]])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(text=texto, parse_mode="HTML", reply_markup=reply_markup)
    return PAY


def pay2(update: Update, context: CallbackContext):
    expenses = db.select("expenses")
    data = db.select("data")
    id_person = int(update.callback_query.data.replace("PAY", ""))
    person = data[data.id == id_person].squeeze()
    expenses = expenses[(expenses.id_person == id_person) & (~expenses.paid)]
    update.callback_query.delete_message()
    text = f"Estos son los gastos sin pagar de <a href='tg://user?id={person.id}'>{person.nombre} {person.apellidos}</a> \nIBAN: {person.num_cuenta}\n"
    context.user_data["oldMessages"] = [context.bot.sendMessage(chat_id=update.effective_chat.id, text=text, parse_mode="HTML")]
    for expense in expenses.itertuples():
        text = f"{expense.date}\n{expense.price}€\n{expense.concept}"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("💳💰 PAGAR 💳💰", callback_data=f"PAY{expense.id}")]])
        filename, file = client_drive.get_file_by_id(expense.id_file)

        if expense.photo:
            context.user_data["oldMessages"].append(
                context.bot.sendPhoto(chat_id=update.effective_chat.id, photo=file, caption=text, reply_markup=reply_markup))
        else:
            context.user_data["oldMessages"].append(
                context.bot.sendDocument(chat_id=update.effective_chat.id, document=file, filename=filename, caption=text, reply_markup=reply_markup))

    total_expenses = expenses.groupby('id_person').agg({'price': 'sum', 'id': lambda x: '-'.join(map(str, x))}).reset_index().squeeze()
    text = f"Pagar todos los gastos de {person.nombre} {person.apellidos}\n{total_expenses.price}€"
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("💳💰 PAGAR TODO 💳💰", callback_data=f"PAY{total_expenses.id}")], [InlineKeyboardButton("Terminar", callback_data=str("END"))]])
    context.user_data["oldMessages"].append(context.bot.sendMessage(chat_id=update.effective_chat.id, text=text, parse_mode="HTML", reply_markup=reply_markup))

    return PAY2


def end_pay(update: Update, context: CallbackContext):
    expenses = db.select("expenses")
    id_expenses = [int(num) for num in update.callback_query.data.replace("PAY", "").split("-")]
    for idx in id_expenses:
        expense = expenses[expenses.id == idx].squeeze()
        db.update_expense_paid(idx)
        client_drive.move_file_to_folder(expense.id_file, client_drive.FOLDER_PAID)
        texto = f"Se te ha pagado el gasto '{expense.concept}' por valor de {expense.price}€ en la fecha {expense.date.strftime('%d/%m/%Y')}"
        context.bot.sendMessage(chat_id=int(expense.id_person), text=texto)

    for callback in context.user_data["oldMessages"]:
        context.bot.deleteMessage(update.effective_chat.id, callback.message_id)
    keyboard = [[InlineKeyboardButton("Continuar", callback_data=str("CONTINUE")),
                 InlineKeyboardButton("Terminar", callback_data=str("END"))]]

    context.bot.sendMessage(update.effective_chat.id, text="Quieres pagar a alguien mas?",
                            reply_markup=InlineKeyboardMarkup(keyboard))
    update_drive_expenses()
    return FINAL_OPTION


def end(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    logger.warning(f"{update.effective_chat.type} -> {context.user_data['user'].apodo} ha salido del comando tesoreria")
    return ConversationHandler.END


def check_iban(iban):
    iban = iban.replace(" ", "")  # Eliminar espacios en blanco
    iban = iban.upper()  # Convertir a mayúsculas
    error = ""
    if len(iban) != 24:
        error = " -La longitud del IBAN debe de ser de 24 digitos"

    if not iban[:2].isalpha():
        error += "\n -Los dos primeros caracteres deben de ser letras"

    if not iban[2:4].isdigit():
        error += "\n -Los 22 ultimos caracteres deben de ser números"

    if error:
        return False, error

    iban_digits = iban[4:] + iban[:4]
    iban_digits = ''.join(str(ord(digit) - ord('A') + 10) if 'A' <= digit <= 'Z' else digit for digit in iban_digits)

    rest = int(iban_digits) % 97

    return rest == 1, "La has liado en algún número, comprueba que estén todos bien"


def account(update: Update, context: CallbackContext):
    update.callback_query.delete_message()
    data = db.select("data")
    person = data[data.id == update.effective_user.id].squeeze()
    if person.num_cuenta:
        message = f"Tu número de cuenta actual es {person.num_cuenta}. Envíame tu nuevo IBAN en el formato ESXX XXXX XXXX XX XXXXXXXXXX"
    else:
        message = "No tienes ningún número de cuenta actualmente. Introduce tu IBAN en el formato ESXX XXXX XXXX XX XXXXXXXXXX"

    keyboard = [[InlineKeyboardButton("CANCELAR", callback_data=f"BACK")]]
    context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, message, reply_markup=InlineKeyboardMarkup(keyboard))
    return IBAN


def account2(update: Update, context: CallbackContext):
    data = db.select("data")
    person = data[data.id == update.effective_user.id].squeeze()
    iban = update.message.text.replace(" ", "").upper()

    valid, error = check_iban(iban)
    context.bot.deleteMessage(update.effective_chat.id, context.user_data["oldMessage"].message_id)
    context.bot.deleteMessage(update.effective_chat.id, update.message.message_id)
    if valid:
        iban = f"{iban[:4]} {iban[4:8]} {iban[8:12]} {iban[12:14]} {iban[14:]}"
        db.update_field_table(idx=person.id, table="data", fields=["num_cuenta"], values=[iban])
        context.bot.sendMessage(update.effective_chat.id, f"El IBAN {iban} se ha actualizado correctamente")
    else:
        context.user_data["oldMessage"] = context.bot.sendMessage(update.effective_chat.id, f"El IBAN {iban} no es válido:\n{error}")
        return IBAN

    return FINAL_OPTION


def update_drive_expenses():
    expenses = db.select("expenses")[["concept", "paid", "price", "date", "id_file", "id_person"]]
    data = db.select("data")
    data["full_name"] = data["nombre"] + " " + data["apellidos"]
    data = data[["id", "full_name"]]
    result = expenses.merge(data, left_on='id_person', right_on='id', how='inner')
    result.drop(['id', 'id_person'], axis=1, inplace=True)
    result['price'] = result['price'].apply(lambda x: f'{x:.2f} €')
    result['date'] = pd.to_datetime(result['date']).dt.strftime('%d/%m/%Y')
    result['id_file'] = 'https://drive.google.com/file/d/' + result['id_file']

    result = result[['full_name', 'date', 'concept', 'price', 'paid', 'id_file']].sort_values(['paid', 'date'])

    sheet = get_sheet(ID_SHEET_EXPENSES)
    clear_sheet(ID_SHEET_EXPENSES, 'Historial', ranged='B3:Z')
    append_data(sheet, 'Historial', 'B3', result.values.tolist())


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler('tesoreria', treasury)],
        states={
            OPTION: [CallbackQueryHandler(end, pattern='^END$'),
                     CallbackQueryHandler(pay, pattern='^PAY$'),
                     CallbackQueryHandler(account, pattern='^ACCOUNT'),
                     CallbackQueryHandler(expenses_state, pattern='^MINE'),
                     CallbackQueryHandler(bote_state),
                     ],
            IBAN: [MessageHandler(Filters.text & ~Filters.command, account2),
                   CallbackQueryHandler(treasury, pattern='^BACK$')],
            POT: [MessageHandler(Filters.text & ~Filters.command, bote2),
                  CallbackQueryHandler(treasury, pattern='^CANCEL$')],
            POT2: [MessageHandler(Filters.text & ~Filters.command, bote3),
                   CallbackQueryHandler(treasury, pattern='^CANCEL$')],
            POT3: [MessageHandler((Filters.photo | Filters.document) & ~Filters.command, bote4),
                   CallbackQueryHandler(treasury, pattern='^CANCEL$')],
            PAY: [CallbackQueryHandler(end, pattern='^END$'),
                  CallbackQueryHandler(treasury, pattern='^BACK'),
                  CallbackQueryHandler(pay2, pattern='^PAY')],
            PAY2: [CallbackQueryHandler(end, pattern='^END$'),
                   CallbackQueryHandler(end_pay, pattern='^PAY')],
            EXPENSES: [CallbackQueryHandler(delete_expense, pattern='^VIEW'),
                       CallbackQueryHandler(edit_expense, pattern='^EDIT'),
                       CallbackQueryHandler(delete_expense, pattern='^DELETE'),
                       CallbackQueryHandler(end, pattern='^END$'),
                       CallbackQueryHandler(treasury, pattern='^BACK$'),
                       CallbackQueryHandler(delete_expense)],
            EDIT_EXPENSE: [
                CallbackQueryHandler(edit_price, pattern='^PRICE$'),
                CallbackQueryHandler(edit_concept, pattern='^CONCEPT$'),
                CallbackQueryHandler(edit_ticket, pattern='^TICKET$'),
                CallbackQueryHandler(expenses_state, pattern='^BACK')],
            EDIT_CONCEPT: [MessageHandler(Filters.text & ~Filters.command, edit_concept2)],
            EDIT_PRICE: [MessageHandler(Filters.text & ~Filters.command, edit_price2)],
            EDIT_TICKET: [MessageHandler((Filters.photo | Filters.document) & ~Filters.command, edit_ticket2)],
            DELETE_EXPENSE: [
                CallbackQueryHandler(delete_expense2, pattern='^DELETE'),
                CallbackQueryHandler(expenses_state, pattern='^BACK')],
            FINAL_OPTION: [
                CallbackQueryHandler(treasury, pattern='^CONTINUE2$'),
                CallbackQueryHandler(expenses_state, pattern='^CONTINUE3$'),
                CallbackQueryHandler(pay, pattern='^CONTINUE$'),
                CallbackQueryHandler(end, pattern='^END')],
        },
        fallbacks=[CommandHandler('tesoreria', treasury)],

    )
