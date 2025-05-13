# AI Travel Assistant

An intelligent travel planning assistant that helps users plan their trips using natural language conversation. The assistant provides personalized itineraries, real-time flight and hotel options, and alternative travel suggestions.

## Features

- Natural language conversation for trip planning
- Real-time flight and hotel data
- Weather information and forecasts
- Personalized itineraries based on user preferences
- Modern, responsive web interface
- Real-time chat interface
- Interactive itinerary display

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn
- pip (Python package manager)
- API keys for:
  - Google Gemini AI
  - Amadeus API (for flights)
  - Hotel API
  - Weather API

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AI_Travel_Assistant.git
cd AI_Travel_Assistant
```

2. Set up the backend:
```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Create .env file for backend
echo "GEMINI_API_KEY=your_gemini_api_key
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
HOTEL_API_KEY=your_hotel_api_key
WEATHER_API_KEY=your_weather_api_key" > .env
```

3. Set up the frontend:
```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install
# or if using yarn
yarn install

# Create .env file for frontend
echo "REACT_APP_API_URL=http://localhost:5000" > .env
```

## Running the Application

1. Start the backend server:
```bash
# Make sure you're in the root directory and virtual environment is activated
python backend/sample.py
```

2. In a new terminal, start the frontend development server:
```bash
# Navigate to frontend directory
cd frontend

# Start the development server
npm start
# or if using yarn
yarn start
```

3. Open your browser and navigate to `http://localhost:3000`

## Project Structure

```
AI_Travel_Assistant/
├── backend/
│   ├── sample.py          # Main application file
│   ├── amadeus_api.py     # Flight data integration
│   ├── hotel_api.py       # Hotel data integration
│   └── weather_api.py     # Weather data integration
├── frontend/
│   ├── public/           # Static files
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── styles/      # CSS and styling
│   │   ├── utils/       # Utility functions
│   │   └── App.js       # Main React component
│   ├── package.json     # Frontend dependencies
│   └── .env            # Frontend environment variables
├── requirements.txt     # Backend Python dependencies
├── .env                # Backend environment variables
└── README.md          # This file
```

## Frontend Features

- Modern, responsive design
- Real-time chat interface
- Interactive itinerary display
- Flight and hotel option cards
- Weather information display
- Alternative route suggestions
- Mobile-friendly layout

## API Integration

The application integrates with several APIs:

1. **Google Gemini AI**: Powers the natural language conversation and itinerary generation
2. **Amadeus API**: Provides real-time flight data and alternative routes
3. **Hotel API**: Offers hotel availability and pricing
4. **Weather API**: Supplies weather forecasts and climatology data

## Development

### Backend Development
- The backend is built with Python and uses Flask for the API
- All API integrations are modular and can be easily extended
- Environment variables are managed using python-dotenv

### Frontend Development
- Built with React.js
- Uses modern React hooks and functional components
- Styled with CSS modules for component-specific styling
- Real-time updates using WebSocket connection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.