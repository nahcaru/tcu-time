const FOLDER_ID_TiE = "1NQUQza1nZ2_6ljrLG72Nc0KBsBP54alG";
const FOLDER_NAME_PDFS = "PDFs";
const FOLDER_NAME_SHEETS = "Sheets";
const HEADER = [
  "period",
  "term",
  "grade",
  "class",
  "name",
  "lecturer",
  "code",
  "room",
  "target",
  "early",
  "note",
  "altName",
  "altTarget",
];

const DEPARTMENTS = [
  "理工学部",
  "理工学部（機械機シを除く）",
  "理工学部（自然を除く）",
  "理工学部（自然）",
  "建築都市デザイン学部",
  "情報工学部",
  "都市生活学部",
  "人間科学部",
];

const YEAR_CODES = [["s21", "t21"], ["s22"], ["s23"], ["s24"]];

const CURRICULUM_CODES = [
  [
    ["s211"],
    ["s2113", "s2114", "s2115", "s2116", "s2117"],
    ["s2111", "s2112", "s2113", "s2114", "s2115", "s2116"],
    ["s2117"],
    ["s212"],
    ["s213"],
    ["t214"],
    ["t215"],
  ],
  [
    ["s221"],
    ["s2213", "s2214", "s2215", "s2216", "s2217"],
    ["s2211", "s2212", "s2213", "s2214", "s2215", "s2216"],
    ["s2217"],
    ["s223"],
    ["s222"],
    ["s224"],
    ["s225"],
  ],
  [
    ["s231"],
    ["s2313", "s2314", "s2315", "s2316", "s2317"],
    ["s2311", "s2312", "s2313", "s2314", "s2315", "s2316"],
    ["s2317"],
    ["s232"],
    ["s233"],
    ["s234"],
    ["s235"],
  ],
  [
    ["s241"],
    ["s2413", "s2414", "s2415", "s2416", "s2417"],
    ["s2411", "s2412", "s2413", "s2414", "s2415", "s2416"],
    ["s2417"],
    ["s242"],
    ["s243"],
    ["s244"],
    ["s245"],
  ],
];

function test() {
  var text = "対象[23-21:理工学部,23-20:建築都市デザイン学部]"
    .replaceAll(" ", "")
    .replaceAll("\n", "")
    .replaceAll(",", "\n");
  targetAlt = text
    .replace("対象[", "")
    .replace("]", "")
    .replace("/\null", "")
    .split("/");
  result = convertText(targetAlt[0].split("\n"));
  console.log(result);
}

function onOpen() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var entries = [
    {
      name: "Download JSON",
      functionName: "toJSON",
    },
  ];
  spreadsheet.addMenu("toJSON", entries);
}

function getJSONFromSheet() {
  let output = {};
  for (sheet of SpreadsheetApp.getActiveSpreadsheet().getSheets()) {
    const data = sheet.getDataRange().getValues();
    const sheetJson = [];
    for (let i = 1; i < data.length - 1; i++) {
      const json = {};
      json[HEADER[0]] = data[i][0].split("\n");
      for (let j = 1; j <= 4; j++) {
        json[HEADER[j]] = data[i][j];
      }
      json[HEADER[5]] = data[i][5].split("\n");
      json[HEADER[6]] = data[i][6];
      for (let j = 7; j <= 8; j++) {
        json[HEADER[j]] = data[i][j].split("\n");
      }
      json[HEADER[9]] = data[i][9] == "0" ? false : true;
      for (let j = 10; j <= 11; j++) {
        json[HEADER[j]] = data[i][j];
      }
      json[HEADER[12]] = data[i][12].split("\n");

      sheetJson.push(json);
    }
    output[sheet.getName()] = sheetJson;
  }
  return JSON.stringify(output);
}

function convertText(originalTexts) {
  // Filter constantArray based on the given conditions
  let result = [];
  for (originalText of originalTexts) {
    // Parse the original text
    const target = originalText.split(":");
    const [start, end] = decode(target[0]);
    if (target.length === 2) {
      const deps = target[1].split("+");
      for (let j = 0; j < DEPARTMENTS.length; j++) {
        if (deps.includes(DEPARTMENTS[j])) {
          for (let i = start; i <= end; i++) {
            result = result.concat(CURRICULUM_CODES[i - 21][j]);
          }
        }
      }
    } else {
      for (let i = start; i <= end; i++) {
        result = result.concat(YEAR_CODES[i - 21]);
      }
    }
  }
  // Join the result array with "\n" and return the converted text
  return result.join("\n");
}

function decode(target) {
  const [e, s] = target.split("-");
  const start = Math.max(parseInt(s), 21);
  const end = Math.min(parseInt(e), 24);
  return [start, end];
}

function generate() {
  // Create a new spreadsheet to save the data
  const spreadSheet = SpreadsheetApp.create("2024後");
  // Move the spreadsheet to Sheets folder
  DriveApp.getFileById(spreadSheet.getId()).moveTo(
    getFolder(FOLDER_NAME_SHEETS),
  );
  for (id of getPdfFiles()) {
    exportToSheets(spreadSheet, convertTablesToValues(readTablesFromPdf(id)));
  }
  spreadSheet.deleteSheet(spreadSheet.getSheets()[0]);

  var onOpenTriggerFunction = "onOpen";
  ScriptApp.newTrigger(onOpenTriggerFunction)
    .forSpreadsheet(spreadSheet.getId())
    .onOpen()
    .create();
}

function getFolder(name) {
  const folders = DriveApp.getFolderById(FOLDER_ID_TiE).getFoldersByName(name);
  if (!folders.hasNext()) return [];
  return folders.next();
}

function getPdfFiles() {
  const files = getFolder(FOLDER_NAME_PDFS).getFilesByType(MimeType.PDF);
  const ids = [];
  while (files.hasNext()) {
    ids.push(files.next().getId());
  }
  return ids;
}

function convertPdfToDoc(id) {
  const pdf = DriveApp.getFileById(id);
  const resource = {
    name: pdf.getName(),
    mimeType: MimeType.GOOGLE_DOCS,
  };
  const options = {
    ocrLanguage: "ja",
  };
  const newFile = Drive.Files.create(resource, pdf.getBlob(), options);
  return DocumentApp.openById(newFile.id);
}

function readTablesFromPdf(id) {
  const doc = convertPdfToDoc(id);
  const tables = doc.getBody().getTables();
  Drive.Files.remove(doc.getId());
  return tables;
}

function convertTablesToValues(tables) {
  const values = [HEADER];
  const department = tables[0].getRow(1).getCell(0).getText().trim();
  for (table of tables) {
    table.removeRow(0);
    const numRows = table.getNumRows();
    const buffer = ["", "", "", ""];
    for (let i = 0; i < numRows; i++) {
      const row = table.getRow(i);
      // 0:department
      const cells = [department];
      // 1:day, 2:period, 3:term, 4:grade
      for (let j = 1; j <= 4; j++) {
        const text = row.getCell(j).getText().trim();
        if (text === "") {
          cells.push(buffer[j - 1]);
        } else {
          cells.push(text);
          buffer[j - 1] = text;
        }
      }
      // 5:class, 6:name, 7:lecturer, 8:code
      for (let j = 5; j <= 8; j++) {
        cells.push(row.getCell(j).getText().trim());
      }
      if (cells[5].includes(" ")) {
        const classSplits = cells[6].split(" ");
        cells[5] = classSplits.shift();
        cells[6] = classSplits.join("");
      }
      if (cells[6].includes(" ")) {
        const splits = cells[6].split(" ");
        if ((cells[7] === "") | cells[6].includes("　")) {
          cells[7] = (splits.pop() + "\n" + cells[7]).trim();
        }
        if (
          (cells[5] === "") &
          (splits.length >= 2) &
          (splits[0].length <= 6) &
          (splits[0] != "SD")
        ) {
          cells[5] = splits.shift();
        }
        const joined = splits.join("");
        if (/[A-Z]/.test(joined)) {
          cells[6] = splits.join(" ");
        } else {
          cells[6] = joined;
        }
      }
      cells[7] = cells[7].replaceAll(" ", "");
      // 9:room, 10:target
      for (let j = 9; j <= 10; j++) {
        cells.push(
          row
            .getCell(j)
            .getText()
            .replaceAll(" ", "")
            .replaceAll("\n", "")
            .replaceAll(",", "\n"),
        );
      }
      if (cells[9].includes("対象[")) {
        const targetSplits = cells[9].split("対象[");
        cells[9] = targetSplits[0];
        cells[10] = targetSplits[1];
      }
      cells[9] = cells[9].replace("-", "");
      if (!cells[10].startsWith("対")) {
        const position = cells[10].indexOf("対");
        cells[9] = cells[10].substring(0, position);
        cells[10] = cells[10].substring(position, cells[10].length - 1);
      }
      targetAlt = cells[10]
        .replace("対象[", "")
        .replace("]", "")
        .replace("/\null", "")
        .split("/");
      cells[10] = convertText(targetAlt[0].split("\n"));
      if (cells[10] === "") {
        continue;
      }
      // 11:early
      cells.push(row.getCell(11).getText().trim() === "" ? 0 : 1);
      // 12:note
      const noteText = row.getCell(12).getText().replaceAll(" ", "");
      if (cells[3].includes("集") | cells[3].includes("通")) {
        cells[2] = "";
        cells.push(noteText);
      } else {
        cells[2] = cells[1] + cells[2];
        if (noteText.includes("対開講")) {
          const period = noteText
            .substring(noteText.indexOf("(") + 1, noteText.indexOf(")"))
            .replaceAll(",", "\n");
          if (cells[2] !== period.split("\n")[0]) {
            continue;
          }
          cells[2] = period;

          cells.push(noteText.replace(/対開講\(.*\)/, "").replace("/", ""));
        } else {
          cells.push(noteText);
        }
      }
      // 13:altName, 14:altTarget
      if (targetAlt.length == 2) {
        const altSplit = targetAlt[1].split(":");
        const [start, end] = decode(altSplit[0]);
        let altTarget = [];
        for (let i = start; i <= end; i++) {
          altTarget = altTarget.concat(YEAR_CODES[i - 21]);
        }
        if (altTarget.length != 0) {
          cells.push(altSplit[1], altTarget.join("\n"));
        } else {
          cells.push("", "");
        }
      } else {
        cells.push("", "");
      }

      cells.splice(0, 2);
      values.push(cells);
    }
  }
  return [department, values];
}

function exportToSheets(spreadSheet, data) {
  const values = data[1];
  const sheet = spreadSheet.insertSheet(data[0]);
  // Set the table data to the sheet
  sheet.getRange(1, 1, values.length, values[0].length).setValues(values);
  sheet
    .getRange(1, 1, values.length, values[0].length)
    .setVerticalAlignment("middle");
}

function toJSON() {
  var download_html =
    HtmlService.createTemplateFromFile("download_dialog").evaluate();
  SpreadsheetApp.getUi().showModalDialog(download_html, "Download JSON");
}
