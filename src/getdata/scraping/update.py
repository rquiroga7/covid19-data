import csv
import json
import datetime


from ..scraping.helpers.utils import (
    undotter,
    get_regions_info,
    git_commit_and_push,
)
from .scraper import get_gov_page, get_minsal_recovered
from ..scraping.helpers.constants import (
    CONFIRMED_CSV_PATH,
    DEATHS_CSV_PATH,
    NATIONAL_REPORT_PATH,
)
from ..processors.generate_consolidated_data import generate


def update_files():
    regions_data = json.loads(get_regions_info())
    gov_data = get_gov_page()
    rows, date = map(gov_data.get, ("rows", "date"))

    # open confirmed file, get data amd check if is updated
    with open(CONFIRMED_CSV_PATH) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        confirmed_header = csv_reader.fieldnames
        if confirmed_header[-1] == date:
            time = datetime.datetime.now()
            print(
                "[{}:{}:{}] The data is already up-to-date".format(
                    time.hour, time.minute, time.second
                )
            )
            return
        confirmed_header.append(date)
        confirmed_data = list(csv_reader)

    # open deaths file and get data
    with open(DEATHS_CSV_PATH) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        deaths_header = csv_reader.fieldnames
        deaths_header.append(date)
        deaths_data = list(csv_reader)

    with open(NATIONAL_REPORT_PATH) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        national_header = csv_reader.fieldnames
        national_data = list(csv_reader)

    dict_per_region = dict()

    # prepare the new gov data

    for row in rows:
        for name_region in regions_data:
            if row[0] == name_region["region"]:
                dict_per_region[regions_data.index(name_region)] = {
                    "region": row[0],
                    "region_id": regions_data.index(name_region) + 1,
                    "new_daily_cases": undotter(row[1]),
                    "confirmed": undotter(row[2]),
                    "deaths": undotter(row[4]),
                }

    # add latest gov confirmed data to csv
    for row in confirmed_data:
        row[date] = str(dict_per_region[int(row["codigo"]) - 1]["confirmed"])
    with open(CONFIRMED_CSV_PATH, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=confirmed_header)
        writer.writeheader()
        writer.writerows(confirmed_data)
    # add latest gov death data to csv
    for row in deaths_data:
        row[date] = str(dict_per_region[int(row["codigo"]) - 1]["deaths"])
    with open(DEATHS_CSV_PATH, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=deaths_header)
        writer.writeheader()
        writer.writerows(deaths_data)

    if date != national_data[-1]["dia"]:
        national_dict = {
            "confirmados": rows[-1][2],
            "dia": date,
            "muertes": rows[-1][4],
            "recuperados": national_data[-1]["recuperados"],
        }
        national_data.append(national_dict)

        with open(NATIONAL_REPORT_PATH, "w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=national_header)
            writer.writeheader()
            writer.writerows(national_data)

    date = datetime.date.today().strftime("%m/%d/%y")
    message = "contagios y muertes al {}".format(date)
    git_commit_and_push(message)


def update_recovered():
    minsal_data = get_minsal_recovered()
    recovered, date = map(minsal_data.get, ("recovered", "date"))

    with open(NATIONAL_REPORT_PATH) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=",")
        national_header = csv_reader.fieldnames
        national_data = list(csv_reader)

    if (
        date == national_data[-1]["dia"]
        and national_data[-1]["recuperados"] == national_data[-2]["recuperados"]
    ):
        national_data[-1]["recuperados"] = recovered
        with open(NATIONAL_REPORT_PATH, "w", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=national_header)
            writer.writeheader()
            writer.writerows(national_data)
        date = datetime.date.today().strftime("%m/%d/%y")
        message = "recuperados al {}".format(date)
        try:
            generate()
        except Exception:
            print("Sorry, failed to generate")
        git_commit_and_push(message)


if __name__ == "__main__":
    a = update_files()
