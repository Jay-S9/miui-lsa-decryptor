/* LSA Decryptor — app code (served as /app.js)
 *
 * Privacy: this file makes NO network requests. It contains no fetch / XMLHttpRequest /
 * sendBeacon / WebSocket calls, and it never builds HTML from file names or file contents.
 * Files are read with the File API, decrypted with Web Crypto in this tab, and written back
 * out as downloads. The page's Content-Security-Policy (vercel.json) enforces the same.
 */

// Queue stub required by Vercel Web Analytics (kept here so the page has no inline scripts)
window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };

// ══════════════════════════════════════════════════════
// AES-128-CTR Decryption — Web Crypto API
// Same key/IV as the Python desktop tool
// ══════════════════════════════════════════════════════

const AES_KEY_HEX = '3082046c30820354a003020102020900';
const AES_IV_BYTES = [17,19,33,35,49,51,65,67,81,83,97,102,103,104,113,114];

// Convert IV bytes to a BigInt counter (matches Python implementation)
function ivToCounter(ivBytes) {
  // Split: first 8 bytes = nonce, last 8 bytes = initial counter value
  // Web Crypto CTR uses a 16-byte counter block directly
  return new Uint8Array(ivBytes.map(b => b & 0xFF));
}

async function getKey() {
  const keyBytes = new Uint8Array(AES_KEY_HEX.match(/.{2}/g).map(h => parseInt(h,16)));
  return crypto.subtle.importKey('raw', keyBytes, { name: 'AES-CTR' }, false, ['decrypt']);
}

async function decryptBuffer(buffer, isVideo) {
  const key = await getKey();
  const iv  = ivToCounter(AES_IV_BYTES);
  const HEADER = 1024;

  if (isVideo && buffer.byteLength > HEADER) {
    // .lsav: only decrypt first 1024 bytes, rest is plain
    const header    = buffer.slice(0, HEADER);
    const body      = buffer.slice(HEADER);
    const decHeader = await crypto.subtle.decrypt(
      { name: 'AES-CTR', counter: iv, length: 64 }, key, header
    );
    // Merge decrypted header + plain body
    const result = new Uint8Array(decHeader.byteLength + body.byteLength);
    result.set(new Uint8Array(decHeader), 0);
    result.set(new Uint8Array(body), decHeader.byteLength);
    return result.buffer;
  } else {
    // .lsa: decrypt entire file
    return crypto.subtle.decrypt(
      { name: 'AES-CTR', counter: iv, length: 64 }, key, buffer
    );
  }
}

function detectExtension(bytes) {
  const b = new Uint8Array(bytes);
  if (b[0]===0xFF && b[1]===0xD8 && b[2]===0xFF)           return '.jpg';
  if (b[0]===0x89 && b[1]===0x50 && b[2]===0x4E && b[3]===0x47) return '.png';
  if (b[4]===0x66 && b[5]===0x74 && b[6]===0x79 && b[7]===0x70) return '.mp4'; // ftyp
  if (b[0]===0x1A && b[1]===0x45 && b[2]===0xDF && b[3]===0xA3) return '.mkv';
  if (b[0]===0x47 && b[1]===0x49 && b[2]===0x46)           return '.gif';
  return '.bin';
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
  return (bytes/1024/1024).toFixed(1) + ' MB';
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
}

// ══ Internationalisation (en / es / id) ══
// English strings are identical to the original page. To add a language: add a dictionary
// below, add an <option> to #lang-select, done. Missing keys fall back to English.
const ORIG_TITLE  = document.title;
const ORIG_DESC   = (document.querySelector('meta[name="description"]') || {}).content || '';
const AUTHOR_LINK = `<a href="https://github.com/Jay-S9" target="_blank" style="color:#3D5566;text-decoration:none">Jay-S9</a>`;

const I18N = {
  en: {
    navHow: `How it works`, navFind: `Find files`, navSupport: `☕ Support`,
    badge: `Free & Open Source`,
    h1: `Recover your<br><span>Secret Album</span> files`,
    heroSub: `Convert .lsa to JPG and .lsav to MP4 from Xiaomi MIUI / HyperOS Secret Album. Free, offline, works on every Xiaomi, Redmi & POCO device.`,
    privacy: `Your files never leave your device — processed entirely in-browser`,
    bylinePrefix: `Original tool by`,
    dropTitle: `Drop .lsa or .lsav files here`, dropTitleTouch: `Tap to choose your .lsa or .lsav files`,
    dropSub: `Photos (.lsa) and videos (.lsav) both supported`,
    browse: `Browse files`, browseTouch: `Choose files`,
    mobileHint: `📱 On your phone? You can decrypt right here — no PC needed.`,
    btnDecrypt: `Decrypt all files`, btnClear: `Clear`,
    zipDefault: `⬇  Download all as ZIP`, zipReady: `⬇  Download all {n} files as ZIP`,
    zipPacking: `⏳  Packing ZIP…`, zipDone: `✓  ZIP downloaded ({n} files)`,
    zipCompressingN: `Compressing {n} files…`, zipGenerating: `Generating ZIP file…`,
    zipPercent: `Compressing… {pct}%`, zipFailed: `ZIP failed — try downloading files individually`,
    processing: `Processing…`, processingFile: `Processing: {name}`, pct: `{pct}%`,
    doneOne: `Done — 1 file decrypted`, doneMany: `Done — {n} files decrypted`,
    toastOne: `1 file decrypted successfully`, toastMany: `{n} files decrypted successfully`,
    toastNone: `No new .lsa or .lsav files found in your selection`,
    trust1: `100% offline — no uploads`, trust2: `Lossless — original quality`,
    trust3: `MIUI 12–14 · HyperOS 1 & 2`, trust4: `Open source on GitHub`,
    howLabel: `// How it works`, howTitle: `Simple. Private. Fast.`,
    step1Title: `Connect your phone`, step1Text: `USB cable → File Transfer mode → copy the secretAlbum folder to your PC`,
    step2Title: `Drop the files`, step2Text: `Drag .lsa photos or .lsav videos directly into the zone above`,
    step2TextTouch: `Tap the box above and choose your .lsa photos or .lsav videos`,
    step3Title: `Click decrypt`, step3Text: `AES-128-CTR decryption runs locally in your browser in seconds`,
    step4Title: `Download & done`, step4Text: `Your JPEG, PNG, or MP4 files download automatically. Original quality.`,
    findLabel: `// Finding your files`, findTitle: `Where are the .lsa files?`,
    findP1: `Connect your Xiaomi phone via USB, enable <strong style="color:var(--text)">File Transfer</strong> mode, then navigate to this path in File Explorer:`,
    pathInternal: `Internal Storage`,
    findP2: `Files will have hashed names like <span style="color:var(--accent)">3e751332435bfad27569ca4efed1b602.lsav</span> — that's normal. These are your encrypted photos (.lsa → JPG/PNG) and videos (.lsav → MP4). Copy the entire secretAlbum folder to your PC before uploading here.`,
    supportTitle: `This tool is free — forever`,
    supportText: `Built by one person to solve a real problem. If it helped you recover photos or videos you thought were lost, consider supporting the project.`,
    btnCoffee: `☕ Buy me a coffee`, btnDownload: `Download app from here`, btnStar: `★ Star on GitHub`,
    footBuilt: `LSA Decryptor — Built by {author} — MIT License`, footContact: `Contact`,
    lightboxClose: `tap or click outside to close`,
    previewTitle: `Click to preview`, remove: `Remove`,
    stReady: `READY`, stWorking: `DECRYPTING…`, stDone: `DONE ✓`, stError: `ERROR`,
    errSmall: `File too small — not a valid .lsa/.lsav file`,
    errKey: `Key error — file may use a different Gallery version`,
    errDecrypt: `Decryption failed — try the desktop app instead`,
    errRead: `File read error — file may be corrupted`,
    errTooLarge: `File too large for the browser version (photos up to 150 MB) — use the desktop app`,
    toastTooMany: `Limit is {n} files at a time — extra files were skipped`,
    zipLimit: `ZIP size limit reached — only some files are included. All files were still downloaded individually.`,
    doneWithErrors: `Done — {ok} decrypted, {fail} failed`,
    toastPartial: `{ok} decrypted, {fail} failed — see the list`,
    toastAllFailed: `No files could be decrypted — see the list`,
  },

  es: {
    navHow: `Cómo funciona`, navFind: `Encontrar archivos`, navSupport: `☕ Apoyar`,
    badge: `Gratis y de código abierto`,
    h1: `Recupera tu<br><span>Álbum secreto</span>`,
    heroSub: `Convierte .lsa a JPG y .lsav a MP4 desde el Álbum secreto de Xiaomi MIUI / HyperOS. Gratis, funciona sin conexión y es compatible con todos los Xiaomi, Redmi y POCO.`,
    privacy: `Tus archivos nunca salen de tu dispositivo: se procesan por completo en el navegador`,
    bylinePrefix: `Herramienta original de`,
    dropTitle: `Suelta aquí tus archivos .lsa o .lsav`, dropTitleTouch: `Toca para elegir tus archivos .lsa o .lsav`,
    dropSub: `Compatible con fotos (.lsa) y videos (.lsav)`,
    browse: `Elegir archivos`, browseTouch: `Elegir archivos`,
    mobileHint: `📱 ¿Desde el móvil? Puedes descifrar aquí mismo, sin necesidad de PC.`,
    btnDecrypt: `Descifrar todos los archivos`, btnClear: `Limpiar`,
    zipDefault: `⬇  Descargar todo en ZIP`, zipReady: `⬇  Descargar los {n} archivos en ZIP`,
    zipPacking: `⏳  Creando ZIP…`, zipDone: `✓  ZIP descargado ({n} archivos)`,
    zipCompressingN: `Comprimiendo {n} archivos…`, zipGenerating: `Generando archivo ZIP…`,
    zipPercent: `Comprimiendo… {pct}%`, zipFailed: `No se pudo crear el ZIP: descarga los archivos uno por uno`,
    processing: `Procesando…`, processingFile: `Procesando: {name}`, pct: `{pct}%`,
    doneOne: `Listo: 1 archivo descifrado`, doneMany: `Listo: {n} archivos descifrados`,
    toastOne: `1 archivo descifrado correctamente`, toastMany: `{n} archivos descifrados correctamente`,
    toastNone: `No se encontraron archivos .lsa o .lsav nuevos en tu selección`,
    trust1: `100 % sin conexión, sin subir nada`, trust2: `Sin pérdida: calidad original`,
    trust3: `MIUI 12–14 · HyperOS 1 y 2`, trust4: `Código abierto en GitHub`,
    howLabel: `// Cómo funciona`, howTitle: `Simple. Privado. Rápido.`,
    step1Title: `Conecta tu teléfono`, step1Text: `Cable USB → modo Transferencia de archivos → copia la carpeta secretAlbum a tu PC`,
    step2Title: `Suelta los archivos`, step2Text: `Arrastra tus fotos .lsa o videos .lsav directamente a la zona de arriba`,
    step2TextTouch: `Toca el recuadro de arriba y elige tus fotos .lsa o videos .lsav`,
    step3Title: `Haz clic en descifrar`, step3Text: `El descifrado AES-128-CTR se ejecuta en tu navegador en cuestión de segundos`,
    step4Title: `Descarga y listo`, step4Text: `Tus archivos JPEG, PNG o MP4 se descargan automáticamente. Calidad original.`,
    findLabel: `// Cómo encontrar tus archivos`, findTitle: `¿Dónde están los archivos .lsa?`,
    findP1: `Conecta tu teléfono Xiaomi por USB, activa el modo <strong style="color:var(--text)">Transferencia de archivos</strong> y ve a esta ruta en el Explorador de archivos:`,
    pathInternal: `Almacenamiento interno`,
    findP2: `Los archivos tendrán nombres con hash como <span style="color:var(--accent)">3e751332435bfad27569ca4efed1b602.lsav</span>; es normal. Son tus fotos cifradas (.lsa → JPG/PNG) y videos (.lsav → MP4). Copia toda la carpeta secretAlbum a tu PC antes de usar esta herramienta.`,
    supportTitle: `Esta herramienta es gratis, para siempre`,
    supportText: `Creada por una sola persona para resolver un problema real. Si te ayudó a recuperar fotos o videos que dabas por perdidos, considera apoyar el proyecto.`,
    btnCoffee: `☕ Invítame un café`, btnDownload: `Descargar la app desde aquí`, btnStar: `★ Dale una estrella en GitHub`,
    footBuilt: `LSA Decryptor — Creado por {author} — Licencia MIT`, footContact: `Contacto`,
    lightboxClose: `toca o haz clic fuera para cerrar`,
    previewTitle: `Haz clic para ver la vista previa`, remove: `Quitar`,
    stReady: `LISTO`, stWorking: `DESCIFRANDO…`, stDone: `HECHO ✓`, stError: `ERROR`,
    errSmall: `Archivo demasiado pequeño: no es un archivo .lsa/.lsav válido`,
    errKey: `Error de clave: el archivo puede usar otra versión de Galería`,
    errDecrypt: `Falló el descifrado: prueba con la app de escritorio`,
    errRead: `Error de lectura: el archivo puede estar dañado`,
    errTooLarge: `Archivo demasiado grande para la versión web (fotos de hasta 150 MB): usa la app de escritorio`,
    toastTooMany: `El límite es de {n} archivos a la vez: se omitieron los demás`,
    zipLimit: `Se alcanzó el límite de tamaño del ZIP: solo se incluyen algunos archivos. Todos se descargaron también por separado.`,
    doneWithErrors: `Listo: {ok} descifrados, {fail} con error`,
    toastPartial: `{ok} descifrados, {fail} con error: revisa la lista`,
    toastAllFailed: `No se pudo descifrar ningún archivo: revisa la lista`,
    metaTitle: `Descifrador LSA y LSAV — Recupera tu Álbum secreto de Xiaomi MIUI / HyperOS gratis`,
    metaDesc: `Herramienta gratuita para descifrar fotos .lsa y videos .lsav del Álbum secreto de Xiaomi MIUI / HyperOS. Convierte lsa a JPG y lsav a MP4 en tu navegador, sin subir archivos ni instalar nada. Compatible con Xiaomi, Redmi y POCO.`,
  },

  id: {
    navHow: `Cara kerja`, navFind: `Cari file`, navSupport: `☕ Dukung`,
    badge: `Gratis & Sumber Terbuka`,
    h1: `Pulihkan<br><span>Album Rahasia</span> Anda`,
    heroSub: `Ubah .lsa menjadi JPG dan .lsav menjadi MP4 dari Album Rahasia Xiaomi MIUI / HyperOS. Gratis, bisa dipakai offline, dan berfungsi di semua perangkat Xiaomi, Redmi & POCO.`,
    privacy: `File Anda tidak pernah meninggalkan perangkat — diproses sepenuhnya di browser`,
    bylinePrefix: `Alat asli oleh`,
    dropTitle: `Letakkan file .lsa atau .lsav di sini`, dropTitleTouch: `Ketuk untuk memilih file .lsa atau .lsav Anda`,
    dropSub: `Mendukung foto (.lsa) dan video (.lsav)`,
    browse: `Pilih file`, browseTouch: `Pilih file`,
    mobileHint: `📱 Pakai HP? Anda bisa mendekripsi langsung di sini — tanpa perlu PC.`,
    btnDecrypt: `Dekripsi semua file`, btnClear: `Hapus`,
    zipDefault: `⬇  Unduh semua dalam ZIP`, zipReady: `⬇  Unduh {n} file dalam ZIP`,
    zipPacking: `⏳  Membuat ZIP…`, zipDone: `✓  ZIP diunduh ({n} file)`,
    zipCompressingN: `Mengompresi {n} file…`, zipGenerating: `Membuat file ZIP…`,
    zipPercent: `Mengompresi… {pct}%`, zipFailed: `Gagal membuat ZIP — unduh file satu per satu`,
    processing: `Memproses…`, processingFile: `Memproses: {name}`, pct: `{pct}%`,
    doneOne: `Selesai — 1 file didekripsi`, doneMany: `Selesai — {n} file didekripsi`,
    toastOne: `1 file berhasil didekripsi`, toastMany: `{n} file berhasil didekripsi`,
    toastNone: `Tidak ada file .lsa atau .lsav baru dalam pilihan Anda`,
    trust1: `100% offline — tanpa unggah`, trust2: `Tanpa kehilangan — kualitas asli`,
    trust3: `MIUI 12–14 · HyperOS 1 & 2`, trust4: `Sumber terbuka di GitHub`,
    howLabel: `// Cara kerja`, howTitle: `Sederhana. Privat. Cepat.`,
    step1Title: `Hubungkan ponsel Anda`, step1Text: `Kabel USB → mode Transfer File → salin folder secretAlbum ke PC Anda`,
    step2Title: `Letakkan file`, step2Text: `Seret foto .lsa atau video .lsav langsung ke area di atas`,
    step2TextTouch: `Ketuk kotak di atas lalu pilih foto .lsa atau video .lsav Anda`,
    step3Title: `Klik dekripsi`, step3Text: `Dekripsi AES-128-CTR berjalan langsung di browser Anda dalam hitungan detik`,
    step4Title: `Unduh & selesai`, step4Text: `File JPEG, PNG, atau MP4 Anda terunduh otomatis. Kualitas asli.`,
    findLabel: `// Mencari file Anda`, findTitle: `Di mana file .lsa berada?`,
    findP1: `Hubungkan ponsel Xiaomi Anda lewat USB, aktifkan mode <strong style="color:var(--text)">Transfer File</strong>, lalu buka jalur ini di File Explorer:`,
    pathInternal: `Penyimpanan internal`,
    findP2: `File akan memiliki nama hash seperti <span style="color:var(--accent)">3e751332435bfad27569ca4efed1b602.lsav</span> — itu normal. Ini adalah foto terenkripsi (.lsa → JPG/PNG) dan video (.lsav → MP4) Anda. Salin seluruh folder secretAlbum ke PC Anda sebelum menggunakan alat ini.`,
    supportTitle: `Alat ini gratis — selamanya`,
    supportText: `Dibuat oleh satu orang untuk memecahkan masalah nyata. Jika alat ini membantu Anda memulihkan foto atau video yang Anda kira hilang, pertimbangkan untuk mendukung proyek ini.`,
    btnCoffee: `☕ Traktir saya kopi`, btnDownload: `Unduh aplikasi dari sini`, btnStar: `★ Beri bintang di GitHub`,
    footBuilt: `LSA Decryptor — Dibuat oleh {author} — Lisensi MIT`, footContact: `Kontak`,
    lightboxClose: `ketuk atau klik di luar untuk menutup`,
    previewTitle: `Klik untuk pratinjau`, remove: `Hapus`,
    stReady: `SIAP`, stWorking: `MENDEKRIPSI…`, stDone: `SELESAI ✓`, stError: `ERROR`,
    errSmall: `File terlalu kecil — bukan file .lsa/.lsav yang valid`,
    errKey: `Kesalahan kunci — file mungkin memakai versi Galeri yang berbeda`,
    errDecrypt: `Dekripsi gagal — coba aplikasi desktop`,
    errRead: `Gagal membaca file — file mungkin rusak`,
    errTooLarge: `File terlalu besar untuk versi web (foto hingga 150 MB) — gunakan aplikasi desktop`,
    toastTooMany: `Batas {n} file sekaligus — file lainnya dilewati`,
    zipLimit: `Batas ukuran ZIP tercapai — hanya sebagian file yang disertakan. Semua file tetap diunduh satu per satu.`,
    doneWithErrors: `Selesai — {ok} didekripsi, {fail} gagal`,
    toastPartial: `{ok} didekripsi, {fail} gagal — lihat daftar`,
    toastAllFailed: `Tidak ada file yang berhasil didekripsi — lihat daftar`,
    metaTitle: `Dekripsi LSA & LSAV — Pulihkan Album Rahasia Xiaomi MIUI / HyperOS Gratis`,
    metaDesc: `Alat gratis untuk mendekripsi foto .lsa dan video .lsav dari Album Rahasia Xiaomi MIUI / HyperOS. Ubah lsa ke JPG dan lsav ke MP4 di browser Anda, tanpa unggah dan tanpa instalasi. Mendukung Xiaomi, Redmi, dan POCO.`,
  },
};

let currentLang = 'en';
let progressLabelState = { key: 'processing', params: null };

// Look up a string (falls back to English, then to the key) and fill {placeholders}
function tr(key, params) {
  const d = I18N[currentLang] || I18N.en;
  let s = d[key] !== undefined ? d[key] : (I18N.en[key] !== undefined ? I18N.en[key] : key);
  if (params) for (const k in params) s = s.split('{' + k + '}').join(params[k]);
  return s;
}

function isTouch() {
  return !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
}

// ?lang=xx (handy for sharing/testing) > saved choice > browser language(s) > English
function detectLang() {
  try { const q = new URLSearchParams(location.search).get('lang'); if (q && I18N[q]) return q; } catch (e) {}
  try { const s = localStorage.getItem('lsa-lang'); if (s && I18N[s]) return s; } catch (e) {}
  const prefs = (navigator.languages && navigator.languages.length) ? navigator.languages : [navigator.language || 'en'];
  for (const p of prefs) {
    let c = String(p).toLowerCase().split('-')[0];
    if (c === 'in') c = 'id';            // legacy code some Android browsers still report for Indonesian
    if (I18N[c]) return c;
  }
  return 'en';
}

function setProgressLabel(key, params) {
  progressLabelState = { key, params: params || null };
  renderProgressLabel();
}
function renderProgressLabel() {
  document.getElementById('progress-label').textContent = tr(progressLabelState.key, progressLabelState.params);
}

function setZipBtn(state, n) {
  const btn = document.getElementById('zip-btn');
  btn.dataset.state = state;
  btn.dataset.n = n === undefined ? '' : n;
  if (state === 'ready' || state === 'default') {      // undo the green/disabled look left by a finished download
    btn.style.pointerEvents = '';
    btn.style.color = '';
    btn.style.borderColor = '';
  }
  renderZipBtn();
}
function renderZipBtn() {
  const btn = document.getElementById('zip-btn');
  const st = btn.dataset.state || 'default';
  const n = btn.dataset.n;
  btn.textContent = st === 'ready'   ? tr('zipReady', { n })
                  : st === 'packing' ? tr('zipPacking')
                  : st === 'done'    ? tr('zipDone', { n })
                  :                    tr('zipDefault');
}

function applyLang(lang, persist) {
  if (!I18N[lang]) lang = 'en';
  currentLang = lang;
  document.documentElement.lang = lang;
  const touch = isTouch();
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = (touch && el.dataset.i18nTouch) ? el.dataset.i18nTouch : el.dataset.i18n;
    el.textContent = tr(key);
  });
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    el.innerHTML = tr(el.dataset.i18nHtml).split('{author}').join(AUTHOR_LINK);
  });
  // English keeps the original title/description exactly; other languages use their own
  document.title = lang === 'en' ? ORIG_TITLE : tr('metaTitle');
  const md = document.querySelector('meta[name="description"]');
  if (md) md.setAttribute('content', lang === 'en' ? ORIG_DESC : tr('metaDesc'));
  const sel = document.getElementById('lang-select');
  if (sel) sel.value = lang;
  renderList(); renderZipBtn(); renderProgressLabel();
  if (persist) { try { localStorage.setItem('lsa-lang', lang); } catch (e) {} }
}

// ══ File queue ══
let fileQueue = [];
let decryptedBlobs = [];  // Stores {filename, blob} for ZIP download

// ── Limits: browser memory is finite (the desktop app has none of these) ──
const MAX_FILES       = 500;                    // files queued at once
const MAX_PHOTO_BYTES = 150 * 1024 * 1024;      // .lsa photos are decrypted fully in memory
const LSAV_HEADER     = 1024;                   // only this many bytes of a .lsav are encrypted
const ZIP_MAX_BYTES   = (window.matchMedia && window.matchMedia('(pointer: coarse)').matches)
                          ? 500 * 1024 * 1024 : 1024 * 1024 * 1024;   // total kept in memory for the ZIP
let retainedBytes = 0;
let zipTruncated  = false;

function addFiles(files) {
  let added = 0, skipped = 0;
  for (const f of files) {
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['lsa','lsav'].includes(ext)) continue;
    if (fileQueue.find(q => q.file.name === f.name && q.file.size === f.size)) continue;
    if (fileQueue.length >= MAX_FILES) { skipped++; continue; }
    fileQueue.push({ file: f, ext, status: 'pending', id: Math.random().toString(36).slice(2) });
    added++;
  }
  if (skipped) showToast(tr('toastTooMany', { n: MAX_FILES }), 'error');
  else if (!added && files.length) showToast(tr('toastNone'), 'error');
  renderList();
}

function renderList() {
  const list = document.getElementById('file-list');
  const actions = document.getElementById('actions');
  list.replaceChildren();

  // Every element is built with createElement + textContent/setAttribute and wired with addEventListener.
  // File names and messages are therefore always plain text — they can never become markup or handlers.
  const make = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };

  fileQueue.forEach(item => {
    const div = make('div', 'file-item');
    div.id = 'item-' + item.id;

    const statusMap = {
      pending: ['pending', tr('stReady')],
      working: ['working', tr('stWorking')],
      done:    ['done',    tr('stDone')],
      error:   ['error',   item.errorKey ? tr(item.errorKey) : (item.errorMsg || tr('stError'))],
    };
    const [cls, label] = statusMap[item.status];
    const ext = item.ext === 'lsav' ? 'lsav' : 'lsa';

    div.appendChild(make('span', 'file-type ' + ext, '.' + ext));
    div.appendChild(make('span', 'file-name', item.file.name));
    div.appendChild(make('span', 'file-size', formatSize(item.file.size)));

    if (item.previewUrl) {
      let thumb;
      if (item.previewType === 'video') {
        thumb = make('span', 'preview-thumb video-thumb', '▶');
        thumb.addEventListener('click', () => openVideoLightbox(item.previewUrl));
      } else {
        thumb = make('img', 'preview-thumb');
        thumb.src = item.previewUrl;
        thumb.addEventListener('click', () => openLightbox(item.previewUrl));
      }
      thumb.title = tr('previewTitle');
      div.appendChild(thumb);
    }

    div.appendChild(make('span', 'file-status ' + cls, label));

    if (item.status === 'pending') {
      const rm = make('button', 'remove-btn', '×');
      rm.setAttribute('aria-label', tr('remove'));
      rm.addEventListener('click', () => removeFile(item.id));
      div.appendChild(rm);
    }
    list.appendChild(div);
  });

  actions.style.display = fileQueue.length ? 'flex' : 'none';
  document.getElementById('decrypt-btn').disabled = !fileQueue.some(f => f.status === 'pending');
}

function revokePreview(item) {            // free the memory held by a preview blob URL
  if (item.previewUrl) { try { URL.revokeObjectURL(item.previewUrl); } catch (e) {} item.previewUrl = null; }
}

function removeFile(id) {
  const it = fileQueue.find(f => f.id === id);
  if (it) revokePreview(it);
  fileQueue = fileQueue.filter(f => f.id !== id);
  renderList();
}

function clearAll() {
  fileQueue.forEach(revokePreview);
  fileQueue = [];
  decryptedBlobs = [];
  retainedBytes = 0;
  zipTruncated = false;
  document.getElementById('zip-btn').classList.remove('visible');
  document.getElementById('zip-progress').classList.remove('visible');
  setZipBtn('default');
  renderList();
  document.getElementById('progress-wrap').classList.remove('visible');
}

function setItemStatus(id, status) {
  const item = fileQueue.find(f => f.id === id);
  if (item) { item.status = status; renderList(); }
}

// ══ Decryption ══
async function startDecryption() {
  const pending = fileQueue.filter(f => f.status === 'pending');
  if (!pending.length) return;

  document.getElementById('decrypt-btn').disabled = true;
  document.getElementById('progress-wrap').classList.add('visible');

  const mimeMap = { '.jpg':'image/jpeg','.png':'image/png','.mp4':'video/mp4','.mkv':'video/x-matroska','.gif':'image/gif','.bin':'application/octet-stream' };
  let done = 0, ok = 0, fail = 0;
  for (const item of pending) {
    setItemStatus(item.id, 'working');
    updateProgress(done, pending.length, item.file.name);

    try {
      const size = item.file.size;
      if (size < 16) throw new Error('File too small — not a valid .lsa/.lsav file');   // minimum size check

      let blob, ext;
      if (item.ext === 'lsav') {
        // Only the first 1024 bytes of a .lsav are encrypted. Read and decrypt just those, then attach the
        // rest of the file untouched — the video body is never loaded into memory or copied.
        const head    = await item.file.slice(0, Math.min(LSAV_HEADER, size)).arrayBuffer();
        const decHead = await decryptBuffer(head, false);
        ext  = detectExtension(decHead);
        blob = new Blob([decHead, item.file.slice(LSAV_HEADER)], { type: mimeMap[ext] || 'application/octet-stream' });
      } else {
        // .lsa photos are encrypted end to end, so they are decrypted in memory — cap the size
        if (size > MAX_PHOTO_BYTES) throw new Error('File too large for the browser version');
        const buf       = await item.file.arrayBuffer();
        const decrypted = await decryptBuffer(buf, false);
        ext  = detectExtension(decrypted);
        blob = new Blob([decrypted], { type: mimeMap[ext] || 'application/octet-stream' });
      }
      const stem    = item.file.name.replace(/\.(lsa|lsav)$/i, '');
      const outName = stem + '_decrypted' + ext;

      // Store preview URL for images and videos
      if (['.jpg', '.png', '.gif'].includes(ext)) {
        item.previewUrl = URL.createObjectURL(blob);
        item.previewType = 'image';
      } else if (ext === '.mp4' || ext === '.mkv') {
        item.previewUrl = URL.createObjectURL(blob);
        item.previewType = 'video';
      }

      // Keep for the ZIP only while the total stays within the memory budget
      if (retainedBytes + blob.size <= ZIP_MAX_BYTES) {
        decryptedBlobs.push({ filename: outName, blob });
        retainedBytes += blob.size;
      } else {
        zipTruncated = true;
      }

      downloadBlob(blob, outName);
      setItemStatus(item.id, 'done');
      ok++;
    } catch (e) {
      // Human-readable error messages (stored as a key so they re-translate if the language changes)
      const raw = e.message || '';
      let key = null;
      if (raw.includes('too small'))        key = 'errSmall';
      else if (raw.includes('too large'))   key = 'errTooLarge';
      else if (raw.includes('key'))         key = 'errKey';
      else if (raw.includes('decrypt'))     key = 'errDecrypt';
      else if (raw.includes('buffer'))      key = 'errRead';
      item.errorKey = key;
      item.errorMsg = raw;
      setItemStatus(item.id, 'error');
      console.error(item.file.name, e);
      fail++;
    }
    done++;
  }

  updateProgress(pending.length, pending.length, '');
  if (fail === 0) {
    setProgressLabel(ok === 1 ? 'doneOne' : 'doneMany', { n: ok });
    showToast(tr(ok === 1 ? 'toastOne' : 'toastMany', { n: ok }), 'success');
  } else {
    setProgressLabel('doneWithErrors', { ok, fail });
    showToast(tr(ok === 0 ? 'toastAllFailed' : 'toastPartial', { ok, fail }), 'error');
  }

  // Show ZIP button if more than one file was decrypted
  if (decryptedBlobs.length > 1) {
    const zipBtn = document.getElementById('zip-btn');
    setZipBtn('ready', decryptedBlobs.length);
    zipBtn.classList.add('visible');
  }
  if (zipTruncated) {
    const zp = document.getElementById('zip-progress');
    zp.textContent = tr('zipLimit');
    zp.classList.add('visible');
  }
}

function updateProgress(current, total, filename) {
  const pct = total ? Math.round((current / total) * 100) : 0;
  document.getElementById('progress-fill').style.width = pct + '%';
  if (filename) setProgressLabel('processingFile', { name: filename });
  else setProgressLabel('pct', { pct });
}

// ══ Drag & drop ══
const zone = document.getElementById('drop-zone');

zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', e => { zone.classList.remove('drag-over'); });
zone.addEventListener('drop', e => {
  e.preventDefault();
  zone.classList.remove('drag-over');
  addFiles([...e.dataTransfer.files]);
});

document.getElementById('file-input').addEventListener('change', e => {
  addFiles([...e.target.files]);
  e.target.value = '';
});

// ══ Toast ══
function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove('show'), 3500);
}


// ══ ZIP Download ══
async function downloadZip() {
  if (!decryptedBlobs.length) return;

  const btn      = document.getElementById('zip-btn');
  const progress = document.getElementById('zip-progress');

  setZipBtn('packing');
  btn.style.pointerEvents = 'none';
  progress.textContent = tr('zipCompressingN', { n: decryptedBlobs.length });
  progress.classList.add('visible');

  try {
    const zip = new JSZip();
    const folder = zip.folder('lsa_decrypted');

    // Two files can share a name (e.g. from different folders) — never let one silently overwrite the other
    const used = new Set();
    const uniqueName = (name) => {
      if (!used.has(name)) { used.add(name); return name; }
      const dot = name.lastIndexOf('.');
      const base = dot > 0 ? name.slice(0, dot) : name, ext = dot > 0 ? name.slice(dot) : '';
      let n = 1, cand;
      do { cand = base + ' (' + (n++) + ')' + ext; } while (used.has(cand));
      used.add(cand); return cand;
    };
    for (const { filename, blob } of decryptedBlobs) {
      folder.file(uniqueName(filename), blob);
    }

    progress.textContent = tr('zipGenerating');

    const zipBlob = await zip.generateAsync(
      { type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } },
      (metadata) => {
        progress.textContent = tr('zipPercent', { pct: metadata.percent.toFixed(0) });
      }
    );

    // Download the ZIP
    const url = URL.createObjectURL(zipBlob);
    const a   = document.createElement('a');
    a.href     = url;
    a.download = `lsa_decrypted_${decryptedBlobs.length}_files.zip`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);

    setZipBtn('done', decryptedBlobs.length);
    btn.style.color = 'var(--success)';
    btn.style.borderColor = 'var(--success)';
    progress.classList.remove('visible');

  } catch (err) {
    setZipBtn('default');
    progress.textContent = tr('zipFailed');
    console.error('ZIP error:', err);
  }
}

// ══ Lightbox ══
function openVideoLightbox(url) {
  const video = document.getElementById('lightbox-video');
  video.src = url;
  document.getElementById('video-lightbox').classList.add('open');
  video.play().catch(() => {});
}
function closeVideoLightbox() {
  const video = document.getElementById('lightbox-video');
  video.pause(); video.src = '';
  document.getElementById('video-lightbox').classList.remove('open');
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeLightbox(); closeVideoLightbox(); } });

function openLightbox(url) {
  document.getElementById('lightbox-img').src = url;
  document.getElementById('lightbox').classList.add('open');
}
function closeLightbox() {
  document.getElementById('lightbox').classList.remove('open');
  document.getElementById('lightbox-img').src = '';
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });


// ══ Event wiring (no inline handlers anywhere — this is what lets the CSP forbid inline scripts) ══
(function () {
  const $ = id => document.getElementById(id);
  $('browse-btn').addEventListener('click', () => $('file-input').click());
  $('decrypt-btn').addEventListener('click', startDecryption);
  $('clear-btn').addEventListener('click', clearAll);
  $('zip-btn').addEventListener('click', downloadZip);
  $('lightbox').addEventListener('click', closeLightbox);
  $('video-lightbox').addEventListener('click', closeVideoLightbox);
  $('lightbox-video').addEventListener('click', e => e.stopPropagation());   // tapping the player must not close it
})();

// ══ Touch-friendly drop zone ══
(function () {
  const input  = document.getElementById('file-input');
  const zoneEl = document.getElementById('drop-zone');
  // Tap anywhere on the zone to open the picker (the Browse button already does)
  zoneEl.addEventListener('click', e => {
    if (e.target === input || e.target.closest('.btn-browse')) return;
    input.click();
  });
})();

// ══ Language init ══
(function () {
  const sel = document.getElementById('lang-select');
  if (sel) sel.addEventListener('change', e => applyLang(e.target.value, true));
  applyLang(detectLang(), false);
})();
