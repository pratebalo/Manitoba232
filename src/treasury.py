from utils.logger_config import logger
import re
import requests
import os
import pandas as pd
import src.utilitys as ut
from datetime import datetime
from utils.sheets_drive import get_sheet, append_data, clear_sheet
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, MessageHandler, filters
from decimal import Decimal

from utils import database as db
from utils import client_drive
from decouple import config

# Stages
OPTION, POT, POT2, POT3, PAY, PAY2, FINAL_OPTION, IBAN, IBAN2, EXPENSES, DELETE_EXPENSE, EDIT_EXPENSE, EDIT_CONCEPT, \
    EDIT_PRICE, EDIT_TICKET, EDIT_CONCEPT2, EDIT_PRICE2, EDIT_TICKET2 = range(18)
ID_MANITOBA = int(config("ID_MANITOBA"))
ID_TESORERIA = int(config("ID_TESORERIA"))
ID_ADMIN = int(config("ID_ADMIN"))
ID_SHEET_EXPENSES = config("ID_SHEET_EXPENSES")


async def treasury(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ut.set_actual_user(update.effective_user.id, context)
    if update.effective_chat.id == ID_MANITOBA:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entró en el comando tesoreria desde Manitoba")
        await update.effective_user.send_message(text="Usa el bot mejor por aquí para no tener que mandar mensajes por el grupo: /tesoreria")
        return ConversationHandler.END
    if update.message:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} entró en el comando tesoreria")
    else:
        await update.callback_query.delete_message()
        logger.warning(f"{context.user_data['user'].apodo} ha vuelto al inicio de tesoreria")

    text = f"<b>¿Qué quieres hacer?</b>"
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
    await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=reply_markup)
    return OPTION


async def expenses_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} accedio al apartado gastos")

    all_expenses = db.select("expenses").sort_values(by=["paid", "id"], ascending=True, ignore_index=True)
    context.user_data["all_expenses"] = all_expenses
    my_expenses = all_expenses[all_expenses.id_person == update.effective_user.id].reset_index()

    text = "No tienes gastos sin pagar" if my_expenses.empty else "Estos son tus gastos:"
    keyboard = []
    for i, expense in my_expenses.iterrows():
        price = "{:.2f}".format(expense.price)
        text += f"\n{i + 1}. {'✅' if expense.paid else '❌'}{price}€ - {expense.date.strftime('%d/%m/%Y')} - {expense.concept}"
        keyboard.append([InlineKeyboardButton(i + 1, callback_data=f"N")])
        if expense.paid:
            keyboard[-1].extend([InlineKeyboardButton(" ", callback_data=f"NOTHING"),
                                 InlineKeyboardButton(" ", callback_data=f"NOTHING")])
        else:
            keyboard[-1].extend([InlineKeyboardButton("✍️", callback_data=f"EDIT{expense.id}"),
                                 InlineKeyboardButton("🗑️", callback_data=f"DELETE{expense.id}")])

    keyboard.append([InlineKeyboardButton("Atras", callback_data=str("BACK")),
                     InlineKeyboardButton("Terminar", callback_data=str("END"))])
    if update.callback_query.message.photo or update.callback_query.message.document:
        await update.callback_query.delete_message()
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    return EXPENSES


async def delete_expense(update: Update, _: ContextTypes.DEFAULT_TYPE):
    id_expense = int(update.callback_query.data.replace("DELETE", ""))

    text = f"¿Seguro que quieres eliminar el gasto?"
    keyboard = [[InlineKeyboardButton("Eliminar", callback_data="DELETE" + str(id_expense)),
                 InlineKeyboardButton("Volver atrás", callback_data="BACK")]]

    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return DELETE_EXPENSE


async def delete_expense2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_expense = int(update.callback_query.data.replace("DELETE", ""))
    expense = db.delete("expenses", id_expense).iloc[0]
    logger.warning(f"{context.user_data['user'].apodo} ha eliminado el gasto '{expense.to_list()}'")
    client_drive.delete_file(expense.id_file)
    await expenses_state(update, context)
    update_drive_expenses()
    return EXPENSES


async def edit_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        if update.callback_query.data == "CANCEL":
            expense = context.user_data["expense"]
            logger.warning(f"{context.user_data['user'].apodo} ha cancelado la edición de {expense.concept}")
        else:
            context.user_data["id_expense"] = int(update.callback_query.data.replace("EDIT", ""))
            all_expenses = db.select("expenses").sort_values(by=["paid", "id"], ascending=True, ignore_index=True)
            expense = all_expenses[all_expenses.id == context.user_data["id_expense"]].squeeze()
            logger.warning(f"{context.user_data['user'].apodo} ha elegido editar el gasto '{expense.to_list()}'")
            context.user_data["expense"] = expense
    else:
        expense = context.user_data["expense"]
        logger.warning(f"{context.user_data['user'].apodo} ha vuelto al gasto '{expense.concept}'")

    expense = context.user_data["expense"]
    if update.callback_query:
        await update.callback_query.delete_message()
    text = f"<b>Seleccione el campo a editar:</b>"
    keyboard = [[InlineKeyboardButton(f"{expense.price}€", callback_data=f"PRICE")],
                [InlineKeyboardButton(expense.concept, callback_data=f"CONCEPT")],
                [InlineKeyboardButton("📷Ticket/Factura📷", callback_data=f"TICKET")],
                [InlineKeyboardButton("CANCELAR", callback_data=f"BACK")]]
    filename, file = client_drive.get_file_by_id(expense.id_file)
    if expense.photo:
        await context.bot.sendPhoto(chat_id=update.effective_chat.id, photo=file, caption=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await context.bot.sendDocument(chat_id=update.effective_chat.id, document=file, filename=filename, caption=text, parse_mode="HTML",
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    return EDIT_EXPENSE


async def edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha eliminado el editar el precio")

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = await update.effective_chat.send_message("Introduce el nuevo precio del gasto", reply_markup=reply_markup)

    return EDIT_PRICE


async def edit_price2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_price = re.sub('[^\\d.]', '', update.message.text.replace(",", ".").replace("'", ".").replace("´", "."))
    logger.warning(f"{context.user_data['user'].apodo} ha introducido el precio {new_price}")
    await update.message.delete()
    await context.user_data["oldMessage"].delete()
    try:
        new_price = float(new_price)

        context.user_data["expense"] = db.update_fields_table(table="expenses", idx=context.user_data["expense"].id, price=new_price)

        await edit_expense(update, context)
        update_drive_expenses()
        return EDIT_EXPENSE

    except ValueError:
        context.user_data["oldMessage"] = await update.effective_chat.send_message(f"La cantidad introducida no es valida, pruebe de nuevo")
        return EDIT_PRICE


async def edit_concept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha eliminado el editar el concepto")
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = await update.effective_chat.send_message("Introduce el numero concepto del gasto", reply_markup=reply_markup)
    return EDIT_CONCEPT


async def edit_concept2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_concept = update.message.text
    logger.warning(f"{context.user_data['user'].apodo} ha introducido el concepto {new_concept}")
    await update.message.delete()
    await context.user_data["oldMessage"].delete()

    context.user_data["expense"] = db.update_fields_table(table="expenses", idx=context.user_data["expense"].id, concept=new_concept)

    await edit_expense(update, context)
    update_drive_expenses()
    return EDIT_EXPENSE


async def edit_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha elegido editar el ticket")
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = await update.effective_chat.send_message("Enviame la foto o archivo con el nuevo ticket", reply_markup=reply_markup)
    return EDIT_TICKET


async def edit_ticket2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = db.select("data")
    logger.warning(f"{context.user_data['user'].apodo} ha enviado ticket")
    if update.message.photo:
        photo = True
        file = await update.message.photo[-1].get_file()
    else:
        photo = False
        file = await update.message.document.get_file()
    data_ticket, ext_ticket = download_file_telegram(file)
    id_expense = context.user_data['expense'].id
    person = data[data.id == update.effective_user.id].squeeze()
    file_name = f"{id_expense}_{person.nombre} {person.apellidos}{ext_ticket}"
    await update.message.delete()
    await context.user_data["oldMessage"].delete()
    file_id = client_drive.upload_file(data=data_ticket, file_name=file_name, parent_id=client_drive.FOLDER_EXPENSES)
    old_file_id = context.user_data["expense"].id_file
    context.user_data["expense"] = db.update_fields_table(table="expenses", idx=id_expense, id_file=file_id, photo=photo)
    client_drive.delete_file(old_file_id)

    await edit_expense(update, context)
    update_drive_expenses()
    return EDIT_EXPENSE


async def bote_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_type"] = update.callback_query.data
    logger.warning(f"{context.user_data['user'].apodo} está añadiendo un gasto")
    if not context.user_data['user'].num_cuenta:
        await account(update, context)
        return IBAN
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = await update.callback_query.edit_message_text(f"¿Cuánto dinero ha sido?", reply_markup=keyboard)

    return POT


async def bote2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} ha enviado la cantidad {update.message.text}")
    context.user_data["price"] = re.sub('[^\\d.]', '', update.message.text.replace(",", ".").replace("'", ".").replace("´", "."))
    await context.user_data["oldMessage"].delete()
    await update.message.delete()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    try:
        float(context.user_data["price"])
        context.user_data["oldMessage"] = await update.effective_chat.send_message(f"¿Cúal es el motivo del gasto?", reply_markup=keyboard)
        return POT2

    except ValueError:
        context.user_data["oldMessage"] = await update.effective_chat.send_message(f"La cantidad introducida no es valida, pruebe de nuevo",
                                                                                   reply_markup=keyboard)

        return POT


async def bote3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} ha enviado el motivo {update.message.text}")

    context.user_data["motivo"] = update.message.text
    await context.user_data["oldMessage"].delete()
    await update.message.delete()

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="CANCEL")]])
    context.user_data["oldMessage"] = await update.effective_chat.send_message(
        f" Necesito que me envies una foto o documento del ticket, si no tienes pues enviame un selfie haciendo el idiota",
        reply_markup=keyboard)

    return POT3


async def bote4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = db.select("data")
    bote = db.select("botes")
    motivo = context.user_data["motivo"]
    persona = data[data.id == update.effective_user.id].squeeze()
    await context.user_data["oldMessage"].delete()
    logger.warning(f"{context.user_data['user'].apodo} ha enviado una foto")
    if context.user_data["expense_type"] == "EXPENSE":
        cantidad = float(context.user_data["price"])
        if update.message.photo:
            photo = True
            file = await update.message.photo[-1].get_file()
            data_ticket, ext_ticket = download_file_telegram(file)
        else:
            photo = False
            file = await update.message.document.get_file()
            data_ticket, ext_ticket = download_file_telegram(file)
        inserted_expense = db.insert_expense(persona.id,
                                             motivo,
                                             cantidad,
                                             datetime.today().strftime('%d/%m/%Y'),
                                             photo)
        expense_id = inserted_expense.id
        file_name = f"{expense_id}_{persona.nombre} {persona.apellidos}{ext_ticket}"

        id_file = client_drive.upload_file(data=data_ticket, file_name=file_name, parent_id=client_drive.FOLDER_EXPENSES)
        db.update_fields_table(table="expenses", idx=expense_id, id_file=id_file)
        treasurer_message = f"{persona.apodo} ha gastado {cantidad}€ en '{motivo}'"
        user_message = f"Has añadido el gasto '{motivo}' por" \
                       f"" \
                       f"" \
                       f"" \
                       f" {cantidad}€"
        filename, file = client_drive.get_file_by_id(id_file)
        if photo:
            await context.bot.sendPhoto(chat_id=ID_TESORERIA, photo=file, caption=treasurer_message)
        else:
            await context.bot.sendDocument(chat_id=ID_TESORERIA, document=file, filename=filename, caption=treasurer_message)
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
        await context.bot.sendMessage(ID_TESORERIA, treasurer_message)

    await update.effective_chat.send_message(user_message)
    update_drive_expenses()
    await treasury(update, context)
    return OPTION


def download_file_telegram(file):
    response = requests.get(file.file_path)
    if response.status_code == 200:
        return response.content, os.path.splitext(file.file_path)[1]

    else:
        logger.warning("Error al descargar la imagen")


async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        keyboardline.append(InlineKeyboardButton(f"{round(expense.price, 2)}€", callback_data="NOTHING"))
        keyboardline.append(InlineKeyboardButton("💰", callback_data="PAY" + str(expense.id_person)))
        keyboard.append(keyboardline)

    keyboard.extend([[InlineKeyboardButton("Atrás", callback_data="BACK"), InlineKeyboardButton("Terminar", callback_data="END")]])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if "oldMessages" in context.user_data:
        for callback in context.user_data["oldMessages"]:
            if callback != update.callback_query.message:
                await callback.delete()
    context.user_data["oldMessages"] = []
    await update.callback_query.delete_message()
    await update.effective_chat.send_message(text=texto, parse_mode="HTML", reply_markup=reply_markup)
    return PAY


async def pay2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expenses = db.select("expenses")
    data = db.select("data")
    id_person = int(update.callback_query.data.replace("PAY", ""))
    person = data[data.id == id_person].squeeze()
    expenses = expenses[(expenses.id_person == id_person) & (~expenses.paid)]
    await update.callback_query.delete_message()
    text = f"Estos son los gastos sin pagar de <a href='tg://user?id={person.id}'>{person.nombre} {person.apellidos}</a> \nIBAN: {person.num_cuenta}\n"
    context.user_data["oldMessages"] = [await update.effective_chat.send_message(text=text, parse_mode="HTML")]
    for expense in expenses.itertuples():
        text = f"{expense.date}\n{expense.price}€\n{expense.concept}"
        keyboard = [[InlineKeyboardButton("💳💰 PAGAR 💳💰", callback_data=f"PAY{expense.id}")]]
        if len(expenses) == 1:
            keyboard.append([InlineKeyboardButton("Seguir pagando", callback_data=str("PAY")),
                             InlineKeyboardButton("Terminar", callback_data=str("END"))])
        reply_markup = InlineKeyboardMarkup(keyboard)
        filename, file = client_drive.get_file_by_id(expense.id_file)

        if expense.photo:
            context.user_data["oldMessages"].append(await update.effective_chat.send_photo(photo=file, caption=text, reply_markup=reply_markup))
        else:
            context.user_data["oldMessages"].append(
                await update.effective_chat.send_document(document=file, filename=filename, caption=text, reply_markup=reply_markup))

    total_expenses = expenses.groupby('id_person').agg({'price': 'sum', 'id': lambda x: '-'.join(map(str, x))}).reset_index().squeeze()
    if len(expenses) > 1:
        text = f"Pagar todos los gastos de {person.nombre} {person.apellidos}\n{round(total_expenses.price, 2)}€"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("💳💰 PAGAR TODO 💳💰", callback_data=f"PAY{total_expenses.id}")],
                                             [InlineKeyboardButton("Seguir pagando", callback_data=str("PAY")),
                                              InlineKeyboardButton("Terminar", callback_data=str("END"))]])
        context.user_data["oldMessages"].append(await update.effective_chat.send_message(text=text, parse_mode="HTML", reply_markup=reply_markup))
    return PAY2


async def end_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expenses = db.select("expenses")
    id_expenses = [int(num) for num in update.callback_query.data.replace("PAY", "").split("-")]
    for idx in id_expenses:
        expense = expenses[expenses.id == idx].squeeze()
        db.update_fields_table(table="expenses", idx=idx, paid=True, paid_date=datetime.today().strftime('%d/%m/%Y'))

        client_drive.move_file_to_folder(expense.id_file, client_drive.FOLDER_PAID)
        texto = f"Se te ha pagado el gasto '{expense.concept}' por valor de {expense.price}€ en la fecha {expense.date.strftime('%d/%m/%Y')}"
        await context.bot.sendMessage(chat_id=int(expense.id_person), text=texto)

    update_drive_expenses()
    await pay(update, context)
    return PAY


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for callback in context.user_data["oldMessages"]:
        if callback != update.callback_query.message:
            await callback.delete()
    context.user_data["oldMessages"] = []
    await update.callback_query.delete_message()
    logger.warning(f"{context.user_data['user'].apodo} ha salido del comando tesoreria")
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


async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f"{context.user_data['user'].apodo} ha elegido cambiar el numero de cuenta")
    await update.callback_query.delete_message()
    data = db.select("data")
    person = data[data.id == update.effective_user.id].squeeze()
    if person.num_cuenta:
        message = f"Tu número de cuenta actual es {person.num_cuenta}. Envíame tu nuevo IBAN en el formato ESXX XXXX XXXX XX XXXXXXXXXX"
    else:
        message = "No tienes ningún número de cuenta actualmente. Introduce tu IBAN en el formato ESXX XXXX XXXX XX XXXXXXXXXX"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("CANCELAR", callback_data=f"BACK")]])
    context.user_data["oldMessage"] = await update.effective_chat.send_message(message, reply_markup=reply_markup)
    return IBAN


async def account2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = db.select("data")
    person = data[data.id == update.effective_user.id].squeeze()
    iban = update.message.text.replace(" ", "").upper()

    valid, error = check_iban(iban)
    await context.user_data["oldMessage"].delete()
    if valid:
        iban = f"{iban[:4]} {iban[4:8]} {iban[8:12]} {iban[12:14]} {iban[14:]}"
        logger.warning(f"{context.user_data['user'].apodo} ha actualizado el iban {iban}")
        db.update_fields_table(table="data", idx=person.id, num_cuenta=iban)
        await update.effective_chat.send_message(f"El IBAN {iban} se ha actualizado correctamente")
        await treasury(update, context)
        return OPTION
    else:
        await update.message.delete()
        logger.warning(f"{context.user_data['user'].apodo} ha introducido mal el iban {iban}")
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("CANCELAR", callback_data=f"BACK")]])
        context.user_data["oldMessage"] = await update.effective_chat.send_message(f"El IBAN {iban} no es válido:\n{error}", reply_markup=reply_markup)
        return IBAN


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
            IBAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, account2),
                   CallbackQueryHandler(treasury, pattern='^BACK$')],
            POT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bote2),
                  CallbackQueryHandler(treasury, pattern='^CANCEL$')],
            POT2: [MessageHandler(filters.TEXT & ~filters.COMMAND, bote3),
                   CallbackQueryHandler(treasury, pattern='^CANCEL$')],
            POT3: [MessageHandler((filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, bote4),
                   CallbackQueryHandler(treasury, pattern='^CANCEL$')],
            PAY: [CallbackQueryHandler(end, pattern='^END$'),
                  CallbackQueryHandler(treasury, pattern='^BACK'),
                  CallbackQueryHandler(pay2, pattern='^PAY')],
            PAY2: [CallbackQueryHandler(end, pattern='^END$'),
                   CallbackQueryHandler(pay, pattern='^PAY$'),
                   CallbackQueryHandler(end_pay, pattern='^PAY')],
            EXPENSES: [CallbackQueryHandler(delete_expense, pattern='^VIEW'),
                       CallbackQueryHandler(edit_expense, pattern='^EDIT'),
                       CallbackQueryHandler(delete_expense, pattern='^DELETE'),
                       CallbackQueryHandler(end, pattern='^END$'),
                       CallbackQueryHandler(treasury, pattern='^BACK$')],
            EDIT_EXPENSE: [
                CallbackQueryHandler(edit_price, pattern='^PRICE$'),
                CallbackQueryHandler(edit_concept, pattern='^CONCEPT$'),
                CallbackQueryHandler(edit_ticket, pattern='^TICKET$'),
                CallbackQueryHandler(expenses_state, pattern='^BACK')],
            EDIT_CONCEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_concept2),
                           CallbackQueryHandler(edit_expense, pattern='^CANCEL')],
            EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_price2),
                         CallbackQueryHandler(edit_expense, pattern='^CANCEL')],
            EDIT_TICKET: [MessageHandler((filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, edit_ticket2),
                          CallbackQueryHandler(edit_expense, pattern='^CANCEL')],
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
