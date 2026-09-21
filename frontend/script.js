const pdfUpload = document.getElementById('pdf-upload');

const uploadBox = document.querySelector('.upload-box');

const uploadButton = document.getElementById('upload-button');

const askButton = document.getElementById('ask-button');

const summariseDocument = document.getElementById('summarise-button');

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


    } catch (error) {
        statusIcon.classList.remove("loading");
        statusIcon.textContent = "❌";
        statusText.textContent = "Failed to read PDF";
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
    try {
        const response = await fetch("http://127.0.0.1:8000/ask", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const result = await response.json();
        document.getElementById('answer').textContent = result.answer;
    } catch (error) {
        document.getElementById('answer').textContent = "Failed to get answer";

    }
});


summariseDocument.addEventListener('click', async function() {
    if (!pdfUpload.files[0]) {
        alert('Please upload a PDF file before summarising.');
        return;
    }

    try {
        const response = await fetch("http://127.0.0.1:8000/summarise", {
            method: 'POST'
        });

        const result = await response.json();

        document.getElementById('answer').textContent = result.answer;

    } catch (error) {
        console.error(error);
        document.getElementById('answer').textContent =
            "Failed to summarise document";
    }
});
