const pdfUpload = document.getElementById('pdf-upload');

const uploadBox = document.querySelector('.upload-box');

pdfUpload.addEventListener('change', function() {

    const file = pdfUpload.files[0];

    if (file) {

        const icon = uploadBox.querySelector('.upload-icon');

        const image = document.createElement('img');

        image.src = 'images/pdf.png';
        image.alt = 'PDF';

        icon.textContent = '';
        icon.appendChild(image);

        uploadBox.querySelector('.upload-text').textContent = file.name;

        uploadBox.querySelector('.upload-subtext').textContent =
            'PDF file selected';
    }

});