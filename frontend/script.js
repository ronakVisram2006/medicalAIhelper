const pdfUpload = document.getElementById('pdf-upload');

const uploadBox = document.querySelector('.upload-box');

const uploadButton = document.getElementById('upload-button');

const openAskButton = document.getElementById('open-ask-button');
const modalOverlay = document.getElementById('ask-modal-overlay');
const closeModalButton = document.getElementById('close-modal-button');

const askButton = document.getElementById('ask-button');

const summariseDocument = document.getElementById('summarise-button');

const uploadButton2 = document.getElementById('upload-button2');

pdfUpload.addEventListener('change', function() {

    const file = pdfUpload.files[0];

    if (!file) {
        return;
    }

    if (file.type !== 'application/pdf') {
        alert('Please select a PDF file.');
        pdfUpload.value = '';
        return;
    }

        const icon = uploadBox.querySelector('.upload-icon');

        const image = document.createElement('img');

        image.src = 'images/pdf.png';
        image.alt = 'PDF';

        icon.textContent = '';
        icon.appendChild(image);

        uploadBox.querySelector('.upload-text').textContent = file.name;

        uploadBox.querySelector('.upload-subtext').textContent =
            'PDF file selected';

    
});
uploadButton.addEventListener('click', async function() {
    if (!pdfUpload.files[0]) {
        alert('Please select a PDF file before uploading.');
        return;
    }

    const uploadStatus = document.getElementById('upload-status');
    const statusIcon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');

    uploadStatus.style.display = "block";
    statusIcon.textContent = "⏳";
    statusIcon.classList.add("loading");
    statusText.textContent = "Uploading and reading PDF...";

    const formData = new FormData();

    formData.append('file', pdfUpload.files[0]);

    try{
        const response = await fetch("http://127.0.0.1:8000/upload", {
        method: 'POST',
        body: formData
    });

    const result = await response.json();
        statusIcon.classList.remove("loading");
        statusIcon.innerHTML = '<img src="images/pdf.png" alt="Success">';
        statusText.textContent = `Succesfully Uploaded and Read PDF: ${result.filename}`;

        const pdfSummary = document.getElementById('pdf-summary');
        pdfSummary.style.display = "block";

        const pages = result.pages;
        let totalWords = 0;

        pages.forEach(page => {
            totalWords += page.text.trim().split(/\s+/).length;
        });

        document.getElementById('summary-pages').textContent =
            `Number of pages: ${pages.length}`;

        document.getElementById('summary-words').textContent =
            `Total words: ${totalWords}`;

        document.getElementsByClassName('upload-container')[0].style.display = "none";

        openAskButton.classList.add('visible');

        uploadButton.style.display = "none";
        uploadButton2.style.display = "inline-block";
    
        



    } catch (error) {
        statusIcon.classList.remove("loading");
        statusIcon.textContent = "❌";
        statusText.textContent = "Failed to read PDF";
    }
});



function highlightFlags(html) {
    html = html.replace(/\((LOW|HIGH|ELEVATED|CRITICAL|NORMAL)\)/gi, function(match, word) {
        return `<span class="flag flag-${word.toLowerCase()}">${word.toUpperCase()}</span>`;
    });
    html = html.replace(/<td>\s*(LOW|HIGH|ELEVATED|CRITICAL|NORMAL)\s*<\/td>/gi, function(match, word) {
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

    answerEl.querySelectorAll('table').forEach(function(table) {
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

    sources.forEach(function(s) {
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
    document.getElementById('question').focus();
}

function closeModal() {
    modalOverlay.classList.remove('open');
}

openAskButton.addEventListener('click', openModal);
closeModalButton.addEventListener('click', closeModal);

// Close when clicking the dark backdrop, but not when clicking inside the modal itself
modalOverlay.addEventListener('click', function(event) {
    if (event.target === modalOverlay) {
        closeModal();
    }
});

// Close on Escape
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && modalOverlay.classList.contains('open')) {
        closeModal();
    }
});

askButton.addEventListener('click', async function() {

    const questionInput = document.getElementById('question');
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
        const response = await fetch("http://127.0.0.1:8000/ask", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const result = await response.json();
        renderAnswer(result.answer);
        renderSources(result.sources);

    } catch (error) {
        document.getElementById('answer').textContent = "Failed to get answer";
        renderSources([]);

    }finally {
        setBusy(false);
    }
});


summariseDocument.addEventListener('click', async function() {
    if (!pdfUpload.files[0]) {
        alert('Please upload a PDF file before summarising.');
        return;
    }

    setBusy(true);
    showLoading('Summarising your document. This can take a little longer...');

    try {
        const response = await fetch("http://127.0.0.1:8000/summarise", {
            method: 'POST'
        });

        const result = await response.json();
        renderAnswer(result.answer);
        renderSources(result.sources);
    } catch (error) {
        console.error(error);
        document.getElementById('answer').textContent = "Failed to summarise document";
        renderSources([]);
    } finally {
        setBusy(false);
    }
});    renderSources([]);


uploadButton2.addEventListener('click', function() {
    if (!confirm('Are you sure you want to upload another PDF? This will reset the current session.')) {
        return;
    }
    pdfUpload.value = '';

    uploadBox.querySelector('.upload-icon').textContent = '↑';
    uploadBox.querySelector('.upload-text').textContent = 'Click to upload your PDF';
    uploadBox.querySelector('.upload-subtext').textContent = 'PDF files only';

    document.getElementsByClassName('upload-container')[0].style.display = "block";
    uploadButton.style.display = "inline-block";

    document.getElementById('upload-status').style.display = "none";
    document.getElementById('pdf-summary').style.display = "none";
    openAskButton.classList.remove('visible');
    uploadButton2.style.display = "none";

    document.getElementById('answer').textContent = 'Your answer will appear here.';
    renderSources([]);
    document.getElementById('question').value = '';
});