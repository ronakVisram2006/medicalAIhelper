const pdfUpload = document.getElementById('pdf-upload');

const uploadBox = document.querySelector('.upload-box');

const uploadButton = document.getElementById('upload-button');

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