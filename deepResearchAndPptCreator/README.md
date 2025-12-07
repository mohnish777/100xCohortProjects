# Research and Presentation Generator

This application combines FastAPI, Gradio, SerpAPI, and Groq to create a powerful research and presentation generation tool. It allows users to input a topic, performs deep research using SerpAPI, processes the information using Groq, and generates a PowerPoint presentation.

## Features

- Web-based interface using Gradio
- Deep research using SerpAPI
- AI-powered content analysis using Groq
- Automatic PowerPoint presentation generation
- RESTful API endpoints using FastAPI

## Prerequisites

- Python 3.8+
- Groq API key
- SerpAPI key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your API keys:
```
GROQ_API_KEY=your_groq_api_key
SERPAPI_API_KEY=your_serpapi_key
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:8000
```

3. Use the web interface to:
   - Enter your research topic
   - Select the number of slides (1-10)
   - Click submit to generate the research and presentation

4. The application will:
   - Perform research on your topic
   - Generate comprehensive content
   - Create a PowerPoint presentation
   - Provide a download link for the presentation

## API Endpoints

- POST `/research`: Perform research and generate presentation
  - Request body:
    ```json
    {
        "topic": "string",
        "num_slides": integer
    }
    ```
  - Response:
    ```json
    {
        "research_content": "string",
        "slides_created": boolean,
        "file_path": "string"
    }
    ```

## Notes

- The application creates a `presentations` directory to store generated PowerPoint files
- Research results are cached to improve performance
- The Groq model used is "mixtral-8x7b-32768"
- SerpAPI search results are limited to 10 results per query

## License

MIT License 