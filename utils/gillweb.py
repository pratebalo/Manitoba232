import requests
import pandas as pd
from io import StringIO
from unidecode import unidecode
from decouple import config

desired_width = 320

pd.set_option('display.width', desired_width)

pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 200)

user = config("USER_GILLWEB")
password = config("PASS_GILLWEB")


def get_data_gillweb():
    data = download_data_gillweb()

    data = filter_data(data)

    data2 = data[(data.father_name != "") & (data.father_email != "")]. \
        groupby(["father_name", "father_surname"]).agg(
        {"complete_name": lambda x: "Padre de " + ", ".join(x),
         "father_email": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "father_phone": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "scout_section": lambda x: tuple(sorted(set(list(
             x.replace('Castor', 'e042ea48c0ca0db').replace('Lobato', '2dca868d8a090f2f')
             .replace('Scout', 'ddb3a430c7d514f').replace('Esculta', '19bd885b8fdf19b3')
             .replace('Rover', '28bd46840ad37aa1')) + ["43b294f70ae0f4a7",
                                                       "myContacts"])))}).reset_index().rename_axis(None, axis=1)
    data3 = data[(data.mother_name != "") & (data.mother_email != "")]. \
        groupby(["mother_name", "mother_surname"]).agg(
        {"complete_name": lambda x: "Madre de " + ", ".join(x),
         "mother_email": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "mother_phone": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "scout_section": lambda x: tuple(sorted(set(list(
             x.replace('Castor', 'e042ea48c0ca0db').replace('Lobato', '2dca868d8a090f2f')
             .replace('Scout', 'ddb3a430c7d514f').replace('Esculta', '19bd885b8fdf19b3')
             .replace('Rover', '28bd46840ad37aa1')) + ["43b294f70ae0f4a7",
                                                       "myContacts"])))}).reset_index().rename_axis(None, axis=1)
    data2.columns = ['givenName', 'familyName', 'biographies', 'emailAddresses', 'phoneNumbers', 'memberships']
    data3.columns = ['givenName', 'familyName', 'biographies', 'emailAddresses', 'phoneNumbers', 'memberships']
    data_final = pd.concat([data2, data3])
    data_final = data_final.sort_values(['givenName', 'familyName']).reset_index(drop=True)
    return data_final


def get_gillweb_csv():
    data = download_data_gillweb()
    # Data to csv format
    data2 = data[(data.father_name != "") & (data.father_email != "")]. \
        groupby(["father_name", "father_surname"]) \
        .agg({"complete_name": lambda x: "Padre de " + ", ".join(x),
              "father_email": lambda x: ", ".join(sorted(set(filter(None, x)))),
              "father_phone": lambda x: ", ".join(sorted(set(filter(None, x)))),
              "scout_section": lambda x: " ::: ".join(
                  set(filter(None, x))) + " ::: Grupo ::: * myContacts"}).reset_index().rename_axis(None, axis=1)
    data3 = data[(data.mother_name != "") & (data.mother_email != "")]. \
        groupby(["mother_name", "mother_surname"]) \
        .agg({"complete_name": lambda x: "Madre de " + ", ".join(x),
              "mother_email": lambda x: ", ".join(sorted(set(filter(None, x)))),
              "mother_phone": lambda x: ", ".join(sorted(set(filter(None, x)))),
              "scout_section": lambda x: " ::: ".join(
                  set(filter(None, x))) + " ::: Grupo ::: * myContacts"}).reset_index().rename_axis(None, axis=1)
    data2.columns = ['Given Name', 'Family Name', 'Notes', 'E-mail 1 - Value', 'Phone 1 - Value', 'Group Membership']
    data3.columns = ['Given Name', 'Family Name', 'Notes', 'E-mail 1 - Value', 'Phone 1 - Value', 'Group Membership']
    data_final = pd.concat([data2, data3])
    data_final.to_csv("contactos.csv", sep=";", index=False)


def download_data_gillweb(section: int = None, subsection: int = None):
    data = []
    for i in range(0, 10):
        try:
            url = "https://www.gillweb.es/core/api.php?controller=user&action=login"
            token = requests.post(url, data={"login": user, "password": password}, timeout=1).json()["data"]

            url = f"https://www.gillweb.es/core/api.php?controller=user&action=exportCSV" \
                  f"&filter%5B0%5D%5B%5D=active&filter%5B0%5D%5B%5D=%3D&filter%5B0%5D%5B%5D=1&token={token}"

            if section:
                url += f"&filter%5B1%5D%5B%5D=scout_subsection.scout_section&filter%5B1%5D%5B%5D=%3D&filter%5B1%5D%5B%5D={section}"

            if subsection:
                url += f"&filter%5B1%5D%5B%5D=scouter_section&filter%5B1%5D%5B%5D=%3D&filter%5B1%5D%5B%5D={subsection}"
            csv = requests.get(url).text

            data = pd.read_csv(StringIO(csv), sep=";", encoding="utf-8",
                               converters={'father_name': str, 'father_surname': str,
                                           'mother_name': str, 'mother_surname': str,
                                           'father_email': str, 'mother_email': str,
                                           'father_phone': str, 'mother_phone': str})
            pd.to_datetime(data['birth_date'])
            data.fillna('', inplace=True)
            break
        except requests.Timeout:
            continue

    return data.copy()


def filter_data(data):
    data = data[
        ["nombre_dni", "surname", "father_name", "father_surname", "father_phone", "father_email", "mother_name",
         "mother_surname", "mother_phone", "mother_email", "scout_subsection", "role"]]
    # print(data[data.father_phone==""])
    data = data[data.scout_subsection != "Scouter"].reset_index()
    data.father_name = data.father_name.apply(unidecode)
    data.father_surname = data.father_surname.apply(unidecode)
    data.mother_name = data.mother_name.apply(unidecode)
    data.mother_surname = data.mother_surname.apply(unidecode)
    data["complete_name"] = data.nombre_dni + " " + data.surname
    data["scout_section"] = data.scout_subsection.str[:-2]
    data = data.sort_values("nombre_dni").reset_index()
    return data


def get_listed_sections():
    data = download_data_gillweb()
    data = data[["nombre_dni", "surname", "scout_subsection", "scouter_section", "birth_date"]]
    data['subsection'] = data.scout_subsection.str.replace(' 1', '').str.replace(' 2', '').str.replace(' 3', '')
    data['scouter_section'] = data.scouter_section.str.replace('Educador ', '').str.replace('de ', '').str.replace(
        'Sección Scout', 'Troperos')
    data['scouter_section'] = data.scouter_section.replace('', 'Sin unidad asignada')

    data.scouter_section = data.scouter_section.astype("category")
    data.scouter_section = data.scouter_section.cat.set_categories(
        ['Castores', 'Lobatos', 'Troperos', 'Escultas', 'Rover', 'Apoyo', 'Sin unidad asignada'])

    sections = []
    for subsection, df_subsection in data.groupby("subsection"):
        df_subsection.sort_values("birth_date", ascending=True, inplace=True)
        df_subsection.drop(['subsection'], axis=1, inplace=True)
        if subsection == "Scouter":
            df_subsection.drop(['scout_subsection'], axis=1, inplace=True)
            df_subsection.sort_values(['scouter_section', 'birth_date'], ascending=[True, True], inplace=True)
        else:
            df_subsection.drop(['scouter_section'], axis=1, inplace=True)

        df_subsection.columns = ['Nombre', 'Apellidos', 'Sección', 'Fecha_de_nacimiento']
        sections.append([subsection, df_subsection])
    sections = sorted(sections, key=lambda x: x[1].Fecha_de_nacimiento.iloc[0], reverse=True)

    return sections
