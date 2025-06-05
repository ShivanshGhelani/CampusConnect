# UCG v2 Admin System

This is the administration system for UCG v2, providing functionality for event management, student registration, and administrative tasks.

## Features

- Event Management
- Student Registration
- Email Integration
- Certificate Generation
- Admin User Management
- Dynamic Event Scheduling
- Comprehensive Feedback System

## Project Structure

```
├── config/          # Configuration files
├── data/           # Data files and templates
├── docs/           # Documentation
├── models/         # Database models
├── routes/         # Route handlers
├── scripts/        # Utility scripts
├── static/         # Static files
├── templates/      # HTML templates
└── utils/          # Utility functions
```

## Setup

1. Clone the repository
```bash
git clone <repository-url>
cd UCG_v2_Admin
```

2. Create and activate virtual environment
```bash
python -m venv admin
admin\Scripts\activate  # On Windows
source admin/bin/activate  # On Unix/MacOS
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
- Copy `.env.example` to `.env`
- Update the variables in `.env` with your configuration

5. Initialize the database
```bash
python scripts/create_admin.py
```

## Running the Application

1. Activate the virtual environment
2. Run the application:
```bash
python main.py
```

## Development

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation as needed

## Testing

Run the tests using:
```bash
python -m pytest
```

## Documentation

Detailed documentation can be found in the `docs/` directory:
- [Certificate Implementation](docs/CERTIFICATE_BUTTON_IMPLEMENTATION.md)
- [Email Integration](docs/EMAIL_TEMPLATE_ENHANCEMENT_SUMMARY.md)
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)
- [Logging](docs/logging.md)
