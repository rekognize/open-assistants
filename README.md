# Open Assistants

Open Assistants is a powerful platform built on OpenAI Assistants, designed to create, manage, test, share, and monitor AI assistants with ease. It enhances usability and manageability beyond what the OpenAI playground offers.

The platform allows users to test their assistants, manage vector stores and files, track usage metrics, and much more. Future updates will introduce support for additional AI backends and expanded functionality.

## Features

- **Comprehensive Assistant Management:** A centralized dashboard to manage assistants, vector stores, files, and their interconnections. 
- **Shareable Assistants:** Generate unique links to share your assistants and enable seamless interaction for others.
- **Usage Monitoring and Analytics:** Access detailed reports on assistant usage and failure points to drive continuous improvement.
- **Enhanced Playground Capabilities:** Edit assistant metadata and descriptions directly within the platform.
- **API Integration (In Progress):** Extend your assistants' functionality by integrating external APIs as tools.
- **Flexible Access Control:** Fine-grained access management to regulate usage and assign admin rights effectively. 

## Technology Stack

- **Backend**: Python, Django (ASGI server recommended for async support)
- **Database**: PostgreSQL (default)
- **AI Integration**: OpenAI API (integrations with other backends are planned)

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Django 4.2 or newer
- ASGI server (e.g., Uvicorn or Daphne) [optional but recommended]

### Installation

1. Clone the repository:
```bash
git clone https://github.com/rekognize/open-assistants.git
```

2. Clone the repository:
```bash
cd open-assistants
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Set up environment variables:

Create a .env file in the project root with the following values:
```bash
SECRET_KEY=<your-Django-secret-key>
OPENAI_API_KEY=<your-openai-api-key>
```

4. Apply database migrations:
```bash
python manage.py migrate
```

5. Start the development server with an ASGI server (e.g., Uvicorn):
```bash
uvicorn open_assistants.asgi:application --reload
```

6. Access the app in your browser at http://127.0.0.1:8000.


## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch: git checkout -b feature-name.
3. Commit your changes: git commit -m "Description of changes".
4. Push to the branch: git push origin feature-name.
5. Open a pull request.


## License

This project is licensed under the MIT License.


## Roadmap

- Advanced function call management
- Multi-Tenant Support: Allow multiple users to manage assistants independently.
