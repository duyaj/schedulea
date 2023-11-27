import re
import requests
import openpyxl
from pdfminer.high_level import extract_text

data = [
    ("10036827", "2019"),
    ("10029936", "2019"),
    ("10039001", "2019"),
    ("10035841", "2020"),
    ("10036158", "2020"),
    ("10035543", "2020"),
    ("10037800", "2019"),
    ("10035141", "2020"),
    ("10040067", "2019"),
    ("10035827", "2020"),
    ("10035882", "2020"),
    ("10035811", "2020"),
    ("10035959", "2019"),
    ("10032359", "2019"),
    ("10034814", "2020"),
    ("10021818", "2018"),
    ("10035821", "2020"),
    ("10029741", "2019"),
    ("10029455", "2019"),
    ("10035838", "2020"),
]

for docid, reportyear in data:
    print(docid, reportyear)
    url = f'https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{reportyear}/{docid}.pdf'

    response = requests.get(url)
    with open('test.pdf', 'wb') as pdf_file:
        pdf_file.write(response.content)

    text = extract_text('test.pdf').lower()

    start = 'schedule a: assets and "unearned" income'
    # use schedule b or c
    end = 'schedule b'

    pattern = rf'{start}(.*?){end}'

    match = re.search(pattern, text, re.DOTALL)

    assets = []
    values = []

    if match:
        extracted_text = match.group(1).strip()

        lines = extracted_text.split('\n')

        # removes lines less than 2 characters (owners)
        filtered_lines = [line for line in lines if len(line) > 2]

        # removes lines that end in > or ?
        filtered_lines = [line for line in filtered_lines if not line.strip().endswith('>') and not line.strip().endswith('?')]

        # filter out keywords
        excluded_keywords = ['asset', 'owner', 'value', 'income', 'type', 'location', 'description', 'gfedc', '\x0casset', '*', 'retirement', 'tax-deferred']
        filtered_lines = [line for line in filtered_lines if not any(line.lower().startswith(keyword) for keyword in excluded_keywords)]

        # gathers asset data
        assets_pattern = re.compile(r'\[\s*([^]]+?)\s*\]')
        assets = [line.strip() for line in filtered_lines if assets_pattern.search(line)]

        # removes assets
        filtered_lines = [line for line in filtered_lines if not any(asset in line for asset in assets)]

        # combines income types if there is more than one
        for i in range(len(filtered_lines) - 1):
            if filtered_lines[i].endswith(','):
                filtered_lines[i] = filtered_lines[i].rstrip(',') + filtered_lines[i + 1]
                filtered_lines[i + 1] = ''

        # removes empty lines
        filtered_lines = [line for line in filtered_lines if line]

        # removes lines greater than 40 characters
        filtered_lines = [line for line in filtered_lines if len(line) <= 25]

        # removes lines starting with $ and without a -
        filtered_lines = [line for line in filtered_lines if not line.startswith('$') or '-' in line]

        try:
            # splits none stuck to other values
            new_filtered_lines = []
            for line in filtered_lines:
                if line.endswith('none') and len(line) > 4:
                    parts = [line[:-4].strip(), 'none']
                    new_filtered_lines.extend(parts)
                else:
                    new_filtered_lines.append(line)

            # replace all occurrences of "none" with "$0"
            new_filtered_lines = [line.replace("none", "$0") for line in new_filtered_lines]

            # traverse through the list and remove "$0" between two strings that start with "$"
            final_filtered_lines = []
            for i in range(len(new_filtered_lines)):
                if i > 0 and i < len(new_filtered_lines) - 1 and new_filtered_lines[i] == "$0" and new_filtered_lines[i - 1].startswith("$") and new_filtered_lines[i + 1].startswith("$"):
                    continue
                final_filtered_lines.append(new_filtered_lines[i])

            final_filtered_lines = filtered_lines

        except:
            break


    # removes everything to the right of the last '-' and the space to the left
    filtered_lines = [re.sub(r'\s*-\s*[^-]*$', '', line) for line in filtered_lines]

    # deletes income values
    i = 0
    while i < len(filtered_lines):
        if not filtered_lines[i].startswith("$"):
            filtered_lines.pop(i)
            if i < len(filtered_lines) and filtered_lines[i].startswith("$"):
                filtered_lines.pop(i)
        else:
            i += 1

    min = filtered_lines

    # to generate the max value
    mapping_dict = {
        '$1': '$1,000',
        '$1,001': '$15,000',
        '$15,001': '$50,000',
        '$50,001': '$100,000',
        '$100,001': '$250,000',
        '$250,001': '$500,000',
        '$500,001': '$1,000,000',
        '$1,000,001': '$5,000,000',
        '$5,000,001': '$25,000,000',
        '$25,000,001': '$50,000,000'
    }

    max = [mapping_dict.get(value, value) for value in min]

    # write asset names, min, max to a spreadsheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    sheet.title = "datascraper"

    sheet.append(["Schedule A"])

    for asset_name, min_val, max_val in zip(assets, min, max):
        sheet.append([asset_name, min_val, max_val])

    workbook.save(f"{docid}.xlsx")

    workbook.close()