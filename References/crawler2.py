import os
import json
import time
import requests
from bs4 import BeautifulSoup

URL = "https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do"
CURRICULUM_CODES = {
    "共通": {
        "s21310",
        "s21311",
        "s22210",
        "s22211",
        "s23310",
        "s23311",
        "s24310",
        "s24311",
        "s21320",
        "s21321",
        "s22220",
        "s22221",
        "s23320",
        "s23321",
        "s24320",
        "s24321",
    },
    "情科": {
        "s21310",
        "s21311",
        "s22210",
        "s22211",
        "s23310",
        "s23311",
        "s24310",
        "s24311",
    },
    "知能": {
        "s21320",
        "s21321",
        "s22220",
        "s22221",
        "s23320",
        "s23321",
        "s24320",
        "s24321",
    },
}


def extract_course_info(tr):
    category_and_compulsory = (
        tr[8].find("td", class_="kougi").text.strip()[1:-1].split("・")
    )
    category = category_and_compulsory[0] if category_and_compulsory else ""
    compulsory = category_and_compulsory[1] if len(category_and_compulsory) > 1 else ""
    credits = tr[16].find("td", class_="kougi").text.strip()
    credits = float(credits) if credits else 0.0
    return category, compulsory, credits


# Check if the file exists
if not os.path.exists("data.json"):
    with open("2024L.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    # If it doesn't, create it with an empty dictionary
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
else:
    with open("updated_data.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)


for key in json_data.keys():
    for data in json_data[key]:
        if "category" not in data.keys():
            data["category"] = {}
            data["compulsory"] = {}
            data["credits"] = {}
        for curriculum_code in CURRICULUM_CODES[key]:
            if (
                any([curriculum_code.startswith(target) for target in data["target"]])
                and curriculum_code not in data["category"].keys()
            ):
                query = {
                    "value(risyunen)": "2024",
                    "value(semekikn)": "1",
                    "value(kougicd)": data["code"],
                    "value(crclumcd)": curriculum_code,
                }
                headers = {"User-Agent": "Syllabus Crawler/1.0.0 (g2221011@tcu.ac.jp)"}
                response = requests.get(URL, headers=headers, params=query)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    syllabus_detail = soup.find("table", class_="syllabus_detail")
                    if syllabus_detail is None:
                        print(
                            f"No syllabus_detail table found.\n{URL}?value(risyunen)=2024&value(semekikn)=1&value(kougicd)={data['code']}&value(crclumcd)={curriculum_code}"
                        )
                        continue
                    tr = syllabus_detail.find_all("tr")
                    category, compulsory, credits = extract_course_info(tr)
                    data["category"][curriculum_code] = category
                    data["compulsory"][curriculum_code] = compulsory
                    data["credits"][curriculum_code] = credits
                    time.sleep(5)
                else:
                    print(
                        f"Status code: {response.status_code}\n{URL}?value(risyunen)=2024&value(semekikn)=1&value(kougicd)={data['code']}&value(crclumcd)={curriculum_code}"
                    )
        with open("updated_data.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        print(data["name"])
