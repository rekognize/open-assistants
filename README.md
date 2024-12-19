# Open Assistants

Open Assistants is an open-source web application for creating, managing, and sharing AI assistants. Built with Python and Django, Open Assistants allows users to test their assistants, manage vector stores and files, track usage, and more. Future updates will expand support to additional AI backends and enhanced functionality.

## Features

- **Create and Test Assistants**: Define the purpose of your assistant, upload files to build its knowledge base, and interact with it.
- **Manage Vector Stores and Files**: Organize and control the knowledge base for each assistant.
- **Share Assistants**: Enable others to interact with your assistants through unique shareable links.
- **Track Usage**: Monitor how your assistants are being used.
- **Function Call Management**: Manage function calls for your assistants (in progress).
- **Future Integrations**: Planned support for additional AI backends beyond OpenAI.

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

- Support for AI backends
- Advanced function call management
- Multi-Tenant Support: Allow multiple users to manage assistants independently.

