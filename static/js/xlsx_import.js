/* =========================================================
   XLSX IMPORT – FRONTEND ONLY
   ========================================================= */

/* ===============================
   KONFIGURACJA – POLA STAŁE
   =============================== */
const XLSX_FIELD_MAP = [

  // Czas i zakres (G12, K12 wg Twojego kodu)
  { source: "G12",     target: "glos_od" },
  { source: "K12",     target: "glos_do" },

  // Dane o kartach (K14 - K24 wg Twojego kodu i standardu)
  { source: "K14",     target: "l_uprawn" },
  { source: "K16",     target: "l_kart_otrzym" },
  { source: "K18",     target: "l_kart_niewyk" }, 
  { source: "K20",     target: "l_kart_wydan" }, 
  
  // Dane z urny
  { source: "K22",     target: "l_kart_wyjet" },
  { source: "K23",     target: "l_kart_wyjet_niewaz" },
  { source: "K24",     target: "l_kart_wyjet_waz" },

  // Wyniki głosowania
  { source: "K26",     target: "l_glos_niewaz" },
  { source: "K27",     target: "l_glos_niewaz_zlyx" },
  { source: "K28",     target: "l_glos_niewaz_inne" },
  { source: "K30",     target: "l_glos_waz" }
];

/* ===============================
   NORMALIZACJA (PL-safe)
   =============================== */
function normalizeKey(str) {
  return str
    .normalize("NFC")
    .trim()
    .toUpperCase();
}

function makeCandidateKey(nazwisko, imie) {
  return `${normalizeKey(nazwisko)}|${normalizeKey(imie)}`;
}

/* ===============================
   XLSX – POBIERANIE WARTOŚCI
   =============================== */
function getValueFromSource(sheet, source) {
  // zakres: bierz pierwszą niepustą
  if (source.includes(":")) {
    const [start, end] = source.split(":");
    for (const addr of [start, end]) {
      const cell = sheet[addr];
      if (cell && cell.v !== undefined && cell.v !== "") {
        return cell.v;
      }
    }
    return "";
  }

  // pojedyncza komórka
  const cell = sheet[source];
  return cell ? cell.v : "";
}

/* ===============================
   MAPOWANIE PÓL STAŁYCH
   =============================== */
function applyStaticFields(workbook) {
  const sheet = workbook.Sheets[workbook.SheetNames[0]];

  XLSX_FIELD_MAP.forEach(cfg => {
    const value = getValueFromSource(sheet, cfg.source);
    if (value === "") return;

    const input = document.querySelector(`[name="${cfg.target}"]`);
    if (!input) return;

    input.value = value;
    input.classList.add("xlsx-filled");
  });
}

/* ===============================
   WYKRYCIE TABELI KANDYDATÓW
   =============================== */
function extractCandidatesFromSheet(sheet) {
  const range = XLSX.utils.decode_range(sheet["!ref"]);
  let headerRow = null;
  let col = {};

  // 1. znajdź wiersz nagłówka
  for (let r = range.s.r; r <= range.e.r; r++) {
    const row = [];

    for (let c = range.s.c; c <= range.e.c; c++) {
      const addr = XLSX.utils.encode_cell({ r, c });
      row.push(sheet[addr]?.v ? String(sheet[addr].v).toUpperCase() : "");
    }

    if (
      row.includes("NAZWISKO") &&
      (row.includes("IMIĘ") || row.includes("IMIE")) &&
      row.some(v => v.includes("GŁOS"))
    ) {
      headerRow = r;

      row.forEach((v, idx) => {
        if (v === "NAZWISKO") col.nazwisko = idx;
        if (v === "IMIĘ" || v === "IMIE") col.imie = idx;
        if (v.includes("GŁOS")) col.glosy = idx;
      });
      break;
    }
  }

  if (headerRow === null) return {};

  // 2. czytaj kandydatów w dół
  const candidates = {};

  for (let r = headerRow + 1; r <= range.e.r; r++) {
    const nazwisko = sheet[XLSX.utils.encode_cell({ r, c: col.nazwisko })]?.v;
    const imie     = sheet[XLSX.utils.encode_cell({ r, c: col.imie })]?.v;
    const glosy    = sheet[XLSX.utils.encode_cell({ r, c: col.glosy })]?.v;

    if (!nazwisko || !imie) break;

    const key = makeCandidateKey(nazwisko, imie);
    candidates[key] = glosy ?? 0;
  }

  return candidates;
}

/* ===============================
   APLIKACJA DO DASHBOARDU
   =============================== */
function applyCandidatesToForm(candidatesMap) {
  const rows = document.querySelectorAll("tr[data-kandydat]");

  rows.forEach(row => {
    const key = row.dataset.kandydat;
    const input = row.querySelector("input");

    if (!input) return;
    if (candidatesMap[key] === undefined) return;

    input.value = candidatesMap[key];
    input.classList.add("xlsx-filled");
  });
}

/* ===============================
   DRAG & DROP
   =============================== */
document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("xlsxDropZone");
  if (!dropZone) return;

 dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragover");

    const file = e.dataTransfer.files[0];
    if (!file || !file.name.endsWith(".xlsx")) {
      alert("Obsługiwane są tylko pliki XLSX");
      return;
    }

    const reader = new FileReader();
    reader.onload = evt => {
      const data = new Uint8Array(evt.target.result);
      const workbook = XLSX.read(data, { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];

      applyStaticFields(workbook);

      const candidatesMap = extractCandidatesFromSheet(sheet);
      applyCandidatesToForm(candidatesMap);

      alert("Dane wczytane z XLSX (tylko frontend – nie zapisano do bazy)");
    };

    reader.readAsArrayBuffer(file);
  });
});
