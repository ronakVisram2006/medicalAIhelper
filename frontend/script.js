import * as pdfjsLib from 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs';

pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs';

const pdfUpload = document.getElementById('pdf-upload');
const uploadBox = document.querySelector('.upload-box');
const uploadButton = document.getElementById('upload-button');
const uploadButton2 = document.getElementById('upload-button2');

const previewCanvas = document.getElementById('pdf-preview');
const previewPlaceholder = document.getElementById('pdf-placeholder');

const openAskButton = document.getElementById('open-ask-button');
const modalOverlay = document.getElementById('ask-modal-overlay');
const closeModalButton = document.getElementById('close-modal-button');

const askButton = document.getElementById('ask-button');
const summariseDocument = document.getElementById('summarise-button');
const questionInput = document.getElementById('question');

const aboutOverlay = document.getElementById('about-modal-overlay');
const aboutLink = document.getElementById('about-link');
const closeAboutButton = document.getElementById('close-about-button');

const historyList = document.getElementById('history-list');

const DB_NAME = 'pdfStore';

let dbPromise;
function openDB() {
    if (!dbPromise) {
        dbPromise = new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, 2);
            req.onupgradeneeded = () => {
                const db = req.result;
                if (db.objectStoreNames.contains('files')) db.deleteObjectStore('files');
                if (db.objectStoreNames.contains('blobs')) db.deleteObjectStore('blobs');
                db.createObjectStore('files', { keyPath: 'id', autoIncrement: true });
                db.createObjectStore('blobs');
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }
    return dbPromise;
}

async function saveFile(file) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(['files', 'blobs'], 'readwrite');
        const req = tx.objectStore('files').add({
            name: file.name,
            size: file.size,
            type: file.type,
            savedAt: Date.now()
        });
        req.onsuccess = () => tx.objectStore('blobs').put(file, req.result);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
    });
}

async function getAllFiles() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const req = db.transaction('files').objectStore('files').getAll();
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

async function getFile(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(['files', 'blobs']);
        const metaReq = tx.objectStore('files').get(id);
        const blobReq = tx.objectStore('blobs').get(id);
        tx.oncomplete = () =>
            resolve(metaReq.result && { ...metaReq.result, blob: blobReq.result });
        tx.onerror = () => reject(tx.error);
    });
}

async function deleteFile(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(['files', 'blobs'], 'readwrite');
        tx.objectStore('files').delete(id);
        tx.objectStore('blobs').delete(id);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
    });
}

async function saveIfNew(file) {
    const files = await getAllFiles();
    const exists = files.some(f => f.name === file.name && f.size === file.size);
    if (!exists) await saveFile(file);
}

async function renderHistory() {
    let files = [];
    try {
        files = (await getAllFiles()).sort((a, b) => b.savedAt - a.savedAt);
    } catch (e) {
        console.warn('Could not load history', e);
    }

    historyList.innerHTML = '';

    if (historyList.parentElement) {
        historyList.parentElement.style.display = files.length ? '' : 'none';
    }

    files.forEach(rec => {
        const row = document.createElement('div');
        row.className = 'history-item';

        const name = document.createElement('span');
        name.textContent = rec.name;

        const del = document.createElement('button');
        del.textContent = '✕';
        del.title = 'Remove from history';
        del.addEventListener('click', async (e) => {
            e.stopPropagation();
            await deleteFile(rec.id);
            renderHistory();
        });

        row.addEventListener('click', () => reuseFile(rec.id));
        row.append(name, del);
        historyList.appendChild(row);
    });
}

async function reuseFile(id) {
    const rec = await getFile(id);
    if (!rec || !rec.blob) return;

    const file = new File([rec.blob], rec.name, { type: rec.type });

    const dt = new DataTransfer();
    dt.items.add(file);
    pdfUpload.files = dt.files;

    pdfUpload.dispatchEvent(new Event('change'));
    uploadButton.click();
}

pdfUpload.addEventListener('change', async function () {
    const file = pdfUpload.files[0];

    if (!file) {
        return;
    }

    if (file.type !== 'application/pdf') {
        alert('Please select a PDF file.');
        pdfUpload.value = '';
        return;
    }

    try {
        const arrayBuffer = await file.arrayBuffer();

        const pdf = await pdfjsLib.getDocument({
            data: arrayBuffer
        }).promise;

        const page = await pdf.getPage(1);

        const containerWidth = uploadBox.clientWidth - 40;
        const originalViewport = page.getViewport({ scale: 1 });
        const scale = containerWidth / originalViewport.width;
        const viewport = page.getViewport({ scale });

        previewCanvas.width = viewport.width;
        previewCanvas.height = viewport.height;

        await page.render({
            canvasContext: previewCanvas.getContext('2d'),
            viewport: viewport
        }).promise;

        previewCanvas.style.display = 'block';
        previewPlaceholder.style.display = 'none';

    } catch (error) {
        console.error('Failed to preview PDF:', error);
        alert('Failed to preview PDF.');
    }
});

uploadButton.addEventListener('click', async function () {
    const file = pdfUpload.files[0];

    if (!file) {
        alert('Please select a PDF file before uploading.');
        return;
    }

    const uploadStatus = document.getElementById('upload-status');
    const statusIcon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');

    uploadStatus.style.display = 'block';
    statusIcon.textContent = '⏳';
    statusIcon.classList.add('loading');
    statusText.textContent = 'Uploading and reading PDF...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('http://127.0.0.1:8000/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed with status ${response.status}`);
        }

        const result = await response.json();

        statusIcon.classList.remove('loading');
        statusIcon.innerHTML = '<img src="images/pdf.png" alt="Success">';
        statusText.textContent = `Successfully Uploaded and Read PDF: ${result.filename}`;

        const pdfSummary = document.getElementById('pdf-summary');
        pdfSummary.style.display = 'block';

        const pages = result.pages;
        let totalWords = 0;

        pages.forEach(page => {
            totalWords += page.text.trim().split(/\s+/).length;
        });

        document.getElementById('summary-pages').textContent =
            `Number of pages: ${pages.length}`;

        document.getElementById('summary-words').textContent =
            `Total words: ${totalWords}`;

        document.getElementsByClassName('upload-container')[0].style.display = 'none';

        openAskButton.classList.add('visible');

        uploadButton.style.display = 'none';
        uploadButton2.style.display = 'inline-block';

        saveIfNew(file)
            .then(renderHistory)
            .catch(e => console.warn('Could not save to history', e));

    } catch (error) {
        console.error(error);
        statusIcon.classList.remove('loading');
        statusIcon.textContent = '❌';
        statusText.textContent = 'Failed to read PDF';
    }
});

function highlightFlags(html) {
    html = html.replace(/\((LOW|HIGH|ELEVATED|CRITICAL|NORMAL)\)/gi, function (match, word) {
        return `<span class="flag flag-${word.toLowerCase()}">${word.toUpperCase()}</span>`;
    });
    html = html.replace(/<td>\s*(LOW|HIGH|ELEVATED|CRITICAL|NORMAL)\s*<\/td>/gi, function (match, word) {
        return `<td><span class="flag flag-${word.toLowerCase()}">${word.toUpperCase()}</span></td>`;
    });
    return html;
}

function renderAnswer(markdownText) {
    const answerEl = document.getElementById('answer');

    if (typeof marked === 'undefined') {
        answerEl.textContent = markdownText;
        return;
    }

    let html = marked.parse(markdownText);
    html = highlightFlags(html);

    answerEl.innerHTML = typeof DOMPurify !== 'undefined'
        ? DOMPurify.sanitize(html)
        : html;

    answerEl.querySelectorAll('table').forEach(function (table) {
        const wrapper = document.createElement('div');
        wrapper.className = 'table-scroll';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
}

function showLoading(message) {
    const answerEl = document.getElementById('answer');
    answerEl.innerHTML =
        '<div class="loading-box"><div class="spinner"></div><span></span></div>';
    answerEl.querySelector('span').textContent = message;
    renderSources([]);
}

function setBusy(busy) {
    askButton.disabled = busy;
    summariseDocument.disabled = busy;
}

function renderSources(sources) {
    const el = document.getElementById('sources');
    el.innerHTML = '';
    if (!sources || sources.length === 0) return;

    const heading = document.createElement('h4');
    heading.textContent = 'Sources';
    el.appendChild(heading);

    sources.forEach(function (s) {
        const location = s.line_start === s.line_end
            ? `Page ${s.page}, line ${s.line_start}`
            : `Page ${s.page}, lines ${s.line_start}–${s.line_end}`;

        const item = document.createElement('div');
        item.className = 'source-item';

        const label = document.createElement('strong');
        label.textContent = `[${s.id}] ${location}`;

        const quote = document.createElement('p');
        quote.textContent = `"${s.quote}"`;

        item.appendChild(label);
        item.appendChild(quote);
        el.appendChild(item);
    });
}

function openModal() {
    modalOverlay.classList.add('open');
    questionInput.focus();
}

function closeModal() {
    modalOverlay.classList.remove('open');
}

openAskButton.addEventListener('click', openModal);
closeModalButton.addEventListener('click', closeModal);

modalOverlay.addEventListener('click', function (event) {
    if (event.target === modalOverlay) {
        closeModal();
    }
});

document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && modalOverlay.classList.contains('open')) {
        closeModal();
    }
});

questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.isComposing) {
        e.preventDefault();
        if (!askButton.disabled) askButton.click();
    }
});

askButton.addEventListener('click', async function () {
    const question = questionInput.value;

    if (!question) {
        alert('Please enter a question.');
        return;
    }
    if (!pdfUpload.files[0]) {
        alert('Please upload a PDF file before asking a question.');
        return;
    }

    setBusy(true);
    showLoading('Reading your document...');

    try {
        const response = await fetch('http://127.0.0.1:8000/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        if (!response.ok) {
            throw new Error(`Ask failed with status ${response.status}`);
        }

        const result = await response.json();
        renderAnswer(result.answer);
        renderSources(result.sources);

    } catch (error) {
        console.error(error);
        document.getElementById('answer').textContent = 'Failed to get answer';
        renderSources([]);

    } finally {
        setBusy(false);
    }
});

summariseDocument.addEventListener('click', async function () {
    if (!pdfUpload.files[0]) {
        alert('Please upload a PDF file before summarising.');
        return;
    }

    setBusy(true);
    showLoading('Summarising your document. This can take a little longer...');

    try {
        const response = await fetch('http://127.0.0.1:8000/summarise', {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`Summarise failed with status ${response.status}`);
        }

        const result = await response.json();
        renderAnswer(result.answer);
        renderSources(result.sources);

    } catch (error) {
        console.error(error);
        document.getElementById('answer').textContent = 'Failed to summarise document';
        renderSources([]);

    } finally {
        setBusy(false);
    }
});

uploadButton2.addEventListener('click', function () {
    if (!confirm('Are you sure you want to upload another PDF? This will reset the current session.')) {
        return;
    }
    pdfUpload.value = '';

    previewCanvas.style.display = 'none';
    previewPlaceholder.style.display = 'block';
    previewPlaceholder.textContent = 'Select a PDF to preview it';

    document.getElementsByClassName('upload-container')[0].style.display = 'block';
    uploadButton.style.display = 'inline-block';

    document.getElementById('upload-status').style.display = 'none';
    document.getElementById('pdf-summary').style.display = 'none';
    openAskButton.classList.remove('visible');
    uploadButton2.style.display = 'none';

    document.getElementById('answer').textContent = 'Your answer will appear here.';
    renderSources([]);
    questionInput.value = '';
});

aboutLink.addEventListener('click', (e) => {
    e.preventDefault();
    aboutOverlay.style.display = 'flex';
});

closeAboutButton.addEventListener('click', () => {
    aboutOverlay.style.display = 'none';
});

aboutOverlay.addEventListener('click', (e) => {
    if (e.target === aboutOverlay) {
        aboutOverlay.style.display = 'none';
    }
});

renderHistory();