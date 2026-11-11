/**
 * AG-PUPUK: Excel Paste Engine & Real-time Matrix Calculation
 * Mendukung copy-paste tabel kuota dari Microsoft Excel / Google Sheets
 * baik via Direct Inline Paste (Ctrl+V di sel input) maupun via Modal Paste.
 */

// Format parsing angka dari Excel (mendukung tanda desimal koma / titik)
function cleanExcelNumber(val) {
  if (val === undefined || val === null) return 0;
  let s = String(val).trim();
  if (!s || s === '-' || s === '–') return 0;

  // Hapus pemisah ribuan titik jika ada koma desimal (format Indo: 1.000,50 -> 1000.50)
  if (s.includes(',') && s.includes('.')) {
    s = s.replace(/\./g, '').replace(',', '.');
  } else if (s.includes(',')) {
    s = s.replace(',', '.');
  }

  // Hapus karakter non-numerik selain minus dan titik
  s = s.replace(/[^0-9.-]/g, '');
  const num = parseFloat(s);
  return isNaN(num) ? 0 : num;
}

/**
 * Mem-parsing teks clipboard TSV/CSV dari Excel
 * @param {string} text - Isi teks dari clipboard
 * @param {number} numCols - Jumlah kolom pupuk yang diharapkan (default: 4)
 * @returns {Array<Array<number>>} Matriks baris x kolom numerik
 */
function parseExcelData(text, numCols = 4) {
  if (!text || !text.trim()) return [];

  const rawLines = text.trim().split(/\r?\n/);
  const resultRows = [];

  for (let line of rawLines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // Lewati baris header jika memuat kata kunci teks tabel
    const upper = trimmed.toUpperCase();
    if (upper.includes('BULAN') || upper.includes('JANUARI') && upper.includes('FEBRUARI') || 
        upper.includes('NPK') && upper.includes('UREA')) {
      continue;
    }
    // Lewati baris total/subtotal
    if (upper.includes('TOTAL') || upper.includes('JUMLAH') || upper.includes('SUBTOTAL')) {
      continue;
    }

    // Split dengan tab (standar Excel) atau semicolon / koma
    let cols = line.split('\t');
    if (cols.length === 1 && line.includes(';')) {
      cols = line.split(';');
    }

    // Ekstraksi nilai numerik
    // Jika baris berisi kolom nama bulan / nomor di depan (misal: "1\tJANUARI\t10\t0\t0\t0")
    // Ambil kolom numerik
    let numbers = [];
    for (let c of cols) {
      const cleaned = cleanExcelNumber(c);
      numbers.push(cleaned);
    }

    // Jika kolom lebih banyak dari numCols, periksa apakah kolom awal adalah teks / nomor urut
    if (numbers.length > numCols) {
      // Ambil numCols kolom terakhir yang biasanya adalah kolom data pupuk
      numbers = numbers.slice(numbers.length - numCols);
    } else while (numbers.length < numCols) {
      numbers.push(0);
    }

    resultRows.push(numbers);
  }

  return resultRows;
}

/**
 * Menghitung ulang subtotal per kecamatan dan grand total secara real-time
 */
function recalculateTableSubtotals(tableEl) {
  if (!tableEl) return;
  const tbody = tableEl.querySelector('tbody');
  if (!tbody) return;

  const dataRows = Array.from(tbody.querySelectorAll('tr:not(.subtotal-row)'));
  if (dataRows.length === 0) return;

  const firstRowInputs = dataRows[0].querySelectorAll('input[type="number"]');
  const numPupuk = firstRowInputs.length;
  const colTotals = new Array(numPupuk).fill(0);

  dataRows.forEach(row => {
    const inputs = row.querySelectorAll('input[type="number"]');
    inputs.forEach((inp, idx) => {
      const val = parseFloat(inp.value) || 0;
      colTotals[idx] += val;
    });
  });

  // Update baris subtotal jika ada
  const subtotalRow = tbody.querySelector('tr.subtotal-row');
  if (subtotalRow) {
    const subtotalCells = subtotalRow.querySelectorAll('td');
    // subtotalCells: 0: "-", 1: "SUBTOTAL", 2..N: nilai per pupuk
    colTotals.forEach((tot, idx) => {
      const cellIdx = 2 + idx;
      if (subtotalCells[cellIdx]) {
        const displayVal = Number.isInteger(tot) ? tot : parseFloat(tot.toFixed(2));
        subtotalCells[cellIdx].textContent = displayVal;
      }
    });
  }

  // Update badge total di header card (jika ada)
  const card = tableEl.closest('.form-card');
  if (card) {
    const badge = card.querySelector('.badge-green');
    if (badge && colTotals.length > 0) {
      const npkTotal = Number.isInteger(colTotals[0]) ? colTotals[0] : parseFloat(colTotals[0].toFixed(2));
      badge.textContent = `Total: ${npkTotal} Ton NPK`;
    }
  }

  // Hitung ulang Rekapitulasi / Grand Total jika ada tabel rekapitulasi di halaman
  recalculateGrandTotal();
}

/**
 * Menghitung ulang seluruh tabel rekapitulasi grand total di halaman
 */
function recalculateGrandTotal() {
  const allTables = document.querySelectorAll('.matrix-input-table');
  let rekapTable = null;
  const dataTables = [];

  allTables.forEach(t => {
    if (t.closest('.form-card')?.innerText.includes('Rekapitulasi Total')) {
      rekapTable = t;
    } else {
      dataTables.push(t);
    }
  });

  if (!rekapTable || dataTables.length === 0) return;

  const rekapRows = rekapTable.querySelectorAll('tbody tr:not(.grand-total-row)');
  const grandTotalRow = rekapTable.querySelector('tbody tr.grand-total-row');
  
  const numPupuk = dataTables[0].querySelectorAll('tbody tr:not(.subtotal-row)')[0]?.querySelectorAll('input[type="number"]').length || 4;
  const grandTotals = new Array(numPupuk).fill(0);

  dataTables.forEach((dTbl, tIdx) => {
    const dRows = Array.from(dTbl.querySelectorAll('tbody tr:not(.subtotal-row)'));
    const tTotals = new Array(numPupuk).fill(0);

    dRows.forEach(r => {
      r.querySelectorAll('input[type="number"]').forEach((inp, pIdx) => {
        const v = parseFloat(inp.value) || 0;
        tTotals[pIdx] += v;
        grandTotals[pIdx] += v;
      });
    });

    // Update row rekapitulasi
    if (rekapRows[tIdx]) {
      const cells = rekapRows[tIdx].querySelectorAll('td');
      tTotals.forEach((tot, pIdx) => {
        const cIdx = 2 + pIdx;
        if (cells[cIdx]) {
          cells[cIdx].textContent = Number.isInteger(tot) ? tot : parseFloat(tot.toFixed(2));
        }
      });
    }
  });

  // Update baris Grand Total
  if (grandTotalRow) {
    const gCells = grandTotalRow.querySelectorAll('td');
    grandTotals.forEach((gtot, pIdx) => {
      const cIdx = 2 + pIdx;
      if (gCells[cIdx]) {
        gCells[cIdx].textContent = Number.isInteger(gtot) ? gtot : parseFloat(gtot.toFixed(2));
      }
    });
  }
}

/**
 * Notifikasi mengambang (Toast Notification)
 */
function showPasteToast(msg, isSuccess = true) {
  let toast = document.getElementById('agPasteToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'agPasteToast';
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      padding: 10px 18px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      transition: all 0.25s ease;
      display: flex;
      align-items: center;
      gap: 8px;
      opacity: 0;
      transform: translateY(10px);
    `;
    document.body.appendChild(toast);
  }

  if (isSuccess) {
    toast.style.background = '#065f46';
    toast.style.color = '#ffffff';
    toast.style.border = '1px solid #047857';
  } else {
    toast.style.background = '#991b1b';
    toast.style.color = '#ffffff';
    toast.style.border = '1px solid #b91c1c';
  }

  toast.innerHTML = msg;
  toast.style.opacity = '1';
  toast.style.transform = 'translateY(0)';

  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
  }, 3500);
}

/**
 * Handler Paste Langsung ke Grid Input Tabel (Inline Spreadsheet Paste)
 */
function attachTableInlinePaste(tableEl) {
  if (!tableEl || tableEl._pasteAttached) return;
  tableEl._pasteAttached = true;

  tableEl.addEventListener('paste', function(e) {
    const target = e.target;
    if (target.tagName !== 'INPUT' || target.type !== 'number') return;

    const clipboardData = e.clipboardData || window.clipboardData;
    if (!clipboardData) return;

    const pasteText = clipboardData.getData('text');
    if (!pasteText) return;

    // Hanya tangani jika data mengandung tab (\t) atau baris baru (\n)
    if (!pasteText.includes('\t') && !pasteText.includes('\n')) {
      return; // Biarkan paste biasa satu angka
    }

    e.preventDefault();

    const tbody = tableEl.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr:not(.subtotal-row)'));
    const targetRow = target.closest('tr');
    const startRowIdx = rows.indexOf(targetRow);
    if (startRowIdx === -1) return;

    const inputsInTargetRow = Array.from(targetRow.querySelectorAll('input[type="number"]'));
    const startColIdx = inputsInTargetRow.indexOf(target);
    if (startColIdx === -1) return;

    const numPupukCols = inputsInTargetRow.length;
    const parsedData = parseExcelData(pasteText, numPupukCols);
    if (parsedData.length === 0) {
      showPasteToast('⚠️ Tidak ada data numerik yang valid dari clipboard.', false);
      return;
    }

    let cellsUpdated = 0;
    parsedData.forEach((rowVals, rOffset) => {
      const currentRIdx = startRowIdx + rOffset;
      if (currentRIdx >= rows.length) return; // Maksimal 12 bulan

      const rInputs = rows[currentRIdx].querySelectorAll('input[type="number"]');
      rowVals.forEach((val, cOffset) => {
        const currentCIdx = startColIdx + cOffset;
        if (currentCIdx < rInputs.length) {
          rInputs[currentCIdx].value = val;
          cellsUpdated++;
        }
      });
    });

    recalculateTableSubtotals(tableEl);
    showPasteToast(`✅ Berhasil menempelkan ${parsedData.length} baris data dari Excel (${cellsUpdated} nilai diperbarui)!`);
  });

  // Pasang listener input untuk hitung otomatis subtotal saat ketik manual
  tableEl.addEventListener('input', function(e) {
    if (e.target.tagName === 'INPUT' && e.target.type === 'number') {
      recalculateTableSubtotals(tableEl);
    }
  });
}

// Inisialisasi otomatis pada seluruh tabel alokasi yang ada di halaman
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.matrix-input-table').forEach(tbl => {
      attachTableInlinePaste(tbl);
      recalculateTableSubtotals(tbl);
    });
  });
}

/**
 * =========================================================================
 * MODAL DIALOG TEMPEL EXCEL (DEDICATED MODAL)
 * =========================================================================
 */
let _activeTargetTable = null;

function getOrCreateExcelModal() {
  let modal = document.getElementById('modalExcelPaste');
  if (modal) return modal;

  const modalHtml = `
    <div id="modalExcelPaste" class="modal-backdrop" style="display: none; z-index: 9990;">
      <div class="modal-box" style="max-width: 620px;">
        <div class="modal-header">
          <div>
            <h3 class="modal-title" style="display: flex; align-items: center; gap: 8px;">
              <span>📋</span> Salin / Tempel Data dari Excel
            </h3>
            <p id="excelModalKecSubtitle" style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">
              Untuk Wilayah: KECAMATAN
            </p>
          </div>
          <button type="button" class="modal-close" onclick="closeExcelModal()">&times;</button>
        </div>

        <div style="margin-bottom: 14px;">
          <label class="form-label">
            Tempelkan Data Excel di Bawah (Ctrl + V):
          </label>
          <textarea id="excelRawTextarea" class="form-textarea" rows="6" 
                    placeholder="Blok sel tabel di Excel (misal: 12 baris x 4 kolom pupuk) -> Tekan Ctrl+C -> Klik di sini -> Tekan Ctrl+V..."
                    style="font-family: var(--font-mono); font-size: 12px; white-space: pre; line-height: 1.4;"></textarea>
          
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; display: flex; justify-content: space-between;">
            <span>💡 Otomatis mendeteksi 12 bulan & membersihkan format desimal/titik ribuan.</span>
            <span id="excelParsedStatus" style="font-weight: 600; color: var(--primary);">0 baris terdeteksi</span>
          </div>
        </div>

        <!-- Preview Grid -->
        <div id="excelPreviewContainer" style="margin-bottom: 16px; max-height: 190px; overflow-y: auto; border: 1px solid var(--border); border-radius: 4px;">
          <table class="matrix-input-table" id="excelPreviewTable" style="font-size: 11.5px;">
            <thead>
              <tr id="excelPreviewHead">
                <th style="width: 35px;">NO</th>
                <th style="text-align: left; padding-left: 8px;">BULAN</th>
                <th>UREA</th>
                <th>NPK</th>
                <th>SP36</th>
                <th>ORGANIK</th>
              </tr>
            </thead>
            <tbody id="excelPreviewBody">
              <tr>
                <td colspan="6" style="padding: 18px; color: var(--text-muted); text-align: center;">
                  Belum ada data. Tempelkan (Ctrl+V) data Excel Anda pada kotak di atas.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="modal-actions" style="justify-content: space-between; align-items: center;">
          <div style="font-size: 11.5px; color: var(--text-secondary);">
            Klik <b>Terapkan</b> untuk mengisi seluruh tabel.
          </div>
          <div style="display: flex; gap: 8px;">
            <button type="button" onclick="closeExcelModal()" class="btn btn-secondary">Batal</button>
            <button type="button" id="btnApplyExcel" onclick="applyExcelDataToTable()" class="btn btn-primary" disabled>
              Terapkan ke Tabel
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modalHtml);
  modal = document.getElementById('modalExcelPaste');

  const textarea = document.getElementById('excelRawTextarea');
  textarea.addEventListener('input', updateExcelModalPreview);

  modal.addEventListener('click', function(e) {
    if (e.target === modal) closeExcelModal();
  });

  return modal;
}

function openExcelModalForTable(triggerBtn) {
  const card = triggerBtn.closest('.form-card') || triggerBtn.closest('.kecamatan-card');
  if (!card) return;

  const table = card.querySelector('.matrix-input-table');
  if (!table) return;

  _activeTargetTable = table;

  // Baca nama kecamatan dari card
  let kecName = 'KECAMATAN';
  const kecInput = card.querySelector('input[type="text"][name*="kecamatan_name"]') || card.querySelector('input[name="kecamatan_list"]');
  const kecHeader = card.querySelector('h3');
  if (kecInput && kecInput.value) {
    kecName = kecInput.value;
  } else if (kecHeader) {
    kecName = kecHeader.textContent.replace('KECAMATAN', '').trim();
  }

  const modal = getOrCreateExcelModal();
  document.getElementById('excelModalKecSubtitle').textContent = `Untuk Wilayah: KECAMATAN ${kecName.toUpperCase()}`;
  document.getElementById('excelRawTextarea').value = '';
  document.getElementById('excelParsedStatus').textContent = '0 baris terdeteksi';
  document.getElementById('btnApplyExcel').disabled = true;

  // Sesuaikan header kolom pratinjau mengikuti urutan kolom tabel target
  const targetHeaders = table.querySelectorAll('thead th');
  if (targetHeaders.length > 0) {
    const headHtml = Array.from(targetHeaders).map((th, idx) => {
      const w = idx === 0 ? 'style="width: 35px;"' : (idx === 1 ? 'style="text-align: left; padding-left: 8px;"' : '');
      return `<th ${w}>${th.textContent.trim()}</th>`;
    }).join('');
    document.getElementById('excelPreviewHead').innerHTML = headHtml;
  }

  // Reset preview table
  document.getElementById('excelPreviewBody').innerHTML = `
    <tr>
      <td colspan="6" style="padding: 18px; color: var(--text-muted); text-align: center;">
        Belum ada data. Tempelkan (Ctrl+V) data Excel Anda pada kotak di atas.
      </td>
    </tr>
  `;

  modal.style.display = 'flex';
  setTimeout(() => {
    document.getElementById('excelRawTextarea').focus();
  }, 100);
}

function closeExcelModal() {
  const modal = document.getElementById('modalExcelPaste');
  if (modal) modal.style.display = 'none';
  _activeTargetTable = null;
}

const BULAN_NAMES = [
  "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
  "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"
];

function updateExcelModalPreview() {
  const textarea = document.getElementById('excelRawTextarea');
  const text = textarea.value;
  const numPupuk = _activeTargetTable ? _activeTargetTable.querySelectorAll('tbody tr:not(.subtotal-row)')[0]?.querySelectorAll('input[type="number"]').length || 4 : 4;
  
  const parsed = parseExcelData(text, numPupuk);
  const statusEl = document.getElementById('excelParsedStatus');
  const btnApply = document.getElementById('btnApplyExcel');
  const tbody = document.getElementById('excelPreviewBody');

  if (parsed.length === 0) {
    statusEl.textContent = '0 baris terdeteksi';
    statusEl.style.color = 'var(--text-muted)';
    btnApply.disabled = true;
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="padding: 18px; color: var(--text-muted); text-align: center;">
          Belum ada data valid. Pastikan data disalin dari tabel angka di Excel.
        </td>
      </tr>
    `;
    return;
  }

  statusEl.textContent = `${parsed.length} baris terdeteksi`;
  statusEl.style.color = '#065f46';
  btnApply.disabled = false;

  let rowsHtml = '';
  for (let b = 0; b < 12; b++) {
    const bNo = b + 1;
    const bNama = BULAN_NAMES[b];
    const vals = parsed[b] || new Array(numPupuk).fill(0);
    const colsHtml = vals.map(v => `<td>${v}</td>`).join('');
    const qClass = (bNo === 3 || bNo === 6 || bNo === 9) ? 'class="quarter-end"' : '';
    rowsHtml += `
      <tr ${qClass}>
        <td style="color: var(--text-muted); font-size: 11px;">${bNo}</td>
        <td class="col-bulan-title">${bNama}</td>
        ${colsHtml}
      </tr>
    `;
  }

  tbody.innerHTML = rowsHtml;
}

function applyExcelDataToTable() {
  if (!_activeTargetTable) return;

  const textarea = document.getElementById('excelRawTextarea');
  const text = textarea.value;
  const targetTbody = _activeTargetTable.querySelector('tbody');
  const rows = Array.from(targetTbody.querySelectorAll('tr:not(.subtotal-row)'));
  const numPupuk = rows[0]?.querySelectorAll('input[type="number"]').length || 4;

  const parsed = parseExcelData(text, numPupuk);
  if (parsed.length === 0) return;

  let cellsUpdated = 0;
  for (let rIdx = 0; rIdx < rows.length; rIdx++) {
    if (rIdx >= parsed.length) break;
    const rowInputs = rows[rIdx].querySelectorAll('input[type="number"]');
    const rowVals = parsed[rIdx];

    rowVals.forEach((val, cIdx) => {
      if (cIdx < rowInputs.length) {
        rowInputs[cIdx].value = val;
        cellsUpdated++;
      }
    });
  }

  recalculateTableSubtotals(_activeTargetTable);
  closeExcelModal();
  showPasteToast(`✅ Berhasil menerapkan ${parsed.length} baris alokasi (${cellsUpdated} nilai diperbarui)!`);
}

