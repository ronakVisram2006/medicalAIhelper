# medicalAIhelper

> An AI-assisted PDF reader that uses LLMs to generate responses to user queries.

##  Overview

medicalAIhelper is an AI-assisted PDF reader designed to make it easier to interact with and understand information contained within PDF documents.

Instead of manually searching through a document to find relevant information, users can ask questions about their PDF and receive AI-generated responses based on its contents.

The project combines a PDF reading experience with Large Language Models (LLMs), using **OpenAI and Groq**, to create a more interactive way of working with documents.

##  Features

*  Read and interact with PDF documents
*  Ask questions about PDF content
* Receive AI-generated responses to user queries
*  Find information without manually searching through the entire document
*  Designed with medical and healthcare-related documents in mind
*  Uses OpenAI and Groq for LLM-powered responses


The application allows users to interact with their documents conversationally rather than relying solely on traditional PDF search.

##  Tech Stack

### AI / LLMs

* **OpenAI** — Large Language Model integration
* **Groq** — Fast LLM inference

### Application

* **Frontend** — PDF reader and user interface
* **Backend** — Application logic and communication with the AI services
* **PDF processing** — Processing and working with PDF content

##  Getting Started

### Prerequisites

Make sure you have the required dependencies installed and API keys configured for the AI services.

### Clone the repository

```bash
git clone https://github.com/ronakVisram2006/medicalAIhelper.git
cd medicalAIhelper
```

### Environment Variables

Create a `.env` file and add the required API credentials:

```env
OPENAI_API_KEY=your_openai_api_key
GROQ_API_KEY=your_groq_api_key
```

Do not commit your API keys to the repository.

### Run the Application

Install the project dependencies and start the frontend/backend services using the project's configured commands.

##  Why We Built It

Medical documents can be lengthy and difficult to navigate. Finding a specific piece of information can require searching through multiple pages and interpreting complex terminology.

medicalAIhelper aims to make this process more interactive by allowing users to ask questions directly about the document they are reading.

##  Future Improvements

* Improve document understanding and context retrieval
* Add conversation history
* Provide references to the relevant sections of the PDF
* Improve handling of complex medical terminology
* Support additional document formats
* Improve PDF navigation alongside AI responses
* Further optimise response speed

##  Disclaimer

medicalAIhelper is an educational/hackathon project and is **not intended to provide medical diagnosis, treatment, or professional medical advice**.

AI-generated responses may contain errors and should be independently verified against reliable medical sources and qualified professionals.

##  Hackathon

Built for **Gateways 2026**.

##  Author

**Ronak Visram**

[GitHub](https://github.com/ronakVisram2006/medicalAIhelper)
