import pymupdf

# function takes in a file and returns text alongside page number
def extract_text_from_pdf(file_path):
    doc = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(doc):
        text = page.get_text()

        pages.append({
            "page_number": page_number + 1,
            "text": text
        })

    doc.close()

    return pages



